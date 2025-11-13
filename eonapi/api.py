"""Eon Next API client."""

import httpx
from datetime import datetime, timedelta
from typing import Optional


class EonNextAPI:
    """Client for interacting with the Eon Next API."""

    def __init__(self):
        self.base_url = "https://api.eonnext-kraken.energy/v1/graphql/"
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires: Optional[int] = None
        self.refresh_expires: Optional[int] = None

    def _current_timestamp(self) -> int:
        """Get current Unix timestamp."""
        return int(datetime.now().timestamp())

    def _is_token_valid(self) -> bool:
        """Check if the current auth token is valid."""
        if not self.auth_token or not self.token_expires:
            return False
        return self.token_expires > self._current_timestamp()

    def _is_refresh_token_valid(self) -> bool:
        """Check if the refresh token is valid."""
        if not self.refresh_token or not self.refresh_expires:
            return False
        return self.refresh_expires > self._current_timestamp()

    async def _graphql_request(
        self,
        operation: str,
        query: str,
        variables: dict = None,
        authenticated: bool = True
    ) -> dict:
        """Make a GraphQL request to the Eon Next API."""
        headers = {}

        if authenticated:
            if not self._is_token_valid():
                raise Exception("Authentication token is not valid")
            headers["authorization"] = f"JWT {self.auth_token}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json={
                    "operationName": operation,
                    "variables": variables or {},
                    "query": query
                },
                headers=headers,
                timeout=30.0
            )

            # Try to get JSON response even on error for better error messages
            try:
                response_data = response.json()
            except Exception:
                response_data = {}

            if not response.is_success:
                error_msg = response_data.get("errors", [{}])[0].get("message", str(response_data))
                raise Exception(f"GraphQL error ({response.status_code}): {error_msg}")

            return response_data

    async def login(self, username: str, password: str) -> bool:
        """Authenticate with username and password."""
        query = """
        mutation loginEmailAuthentication($input: ObtainJSONWebTokenInput!) {
            obtainKrakenToken(input: $input) {
                payload
                refreshExpiresIn
                refreshToken
                token
                __typename
            }
        }
        """

        try:
            result = await self._graphql_request(
                "loginEmailAuthentication",
                query,
                {"input": {"email": username, "password": password}},
                authenticated=False
            )

            if "data" in result and "obtainKrakenToken" in result["data"]:
                token_data = result["data"]["obtainKrakenToken"]
                self.auth_token = token_data["token"]
                self.refresh_token = token_data["refreshToken"]
                self.token_expires = token_data["payload"]["exp"]
                self.refresh_expires = token_data["refreshExpiresIn"]
                return True

            return False
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    async def get_account_numbers(self) -> list[str]:
        """Get all account numbers for the authenticated user."""
        query = """
        query headerGetLoggedInUser {
            viewer {
                accounts {
                    ... on AccountType {
                        number
                        __typename
                    }
                    __typename
                }
                __typename
            }
        }
        """

        result = await self._graphql_request("headerGetLoggedInUser", query)

        if "data" not in result or "viewer" not in result["data"]:
            raise Exception("Failed to retrieve accounts")

        accounts = result["data"]["viewer"]["accounts"]
        return [acc["number"] for acc in accounts]

    async def get_meters(self, account_number: str) -> list[dict]:
        """Get all meters for an account."""
        query = """
        query getAccountMeterSelector($accountNumber: String!, $showInactive: Boolean!) {
            properties(accountNumber: $accountNumber) {
                electricityMeterPoints {
                    id
                    mpan
                    meters(includeInactive: $showInactive) {
                        id
                        serialNumber
                        registers {
                            id
                            name
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                gasMeterPoints {
                    id
                    mprn
                    meters(includeInactive: $showInactive) {
                        id
                        serialNumber
                        registers {
                            id
                            name
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                __typename
            }
        }
        """

        result = await self._graphql_request(
            "getAccountMeterSelector",
            query,
            {"accountNumber": account_number, "showInactive": False}
        )

        if "data" not in result or "properties" not in result["data"]:
            raise Exception("Failed to retrieve meters")

        meters = []
        for prop in result["data"]["properties"]:
            # Process electricity meters
            for mp in prop.get("electricityMeterPoints", []):
                for meter in mp.get("meters", []):
                    meters.append({
                        "type": "electricity",
                        "serial": meter["serialNumber"],
                        "id": meter["id"],
                        "meter_point_id": mp["id"],
                        "mpan": mp.get("mpan", ""),
                    })

            # Process gas meters
            for mp in prop.get("gasMeterPoints", []):
                for meter in mp.get("meters", []):
                    meters.append({
                        "type": "gas",
                        "serial": meter["serialNumber"],
                        "id": meter["id"],
                        "meter_point_id": mp["id"],
                        "mprn": mp.get("mprn", ""),
                    })

        return meters

    async def get_consumption_data(
        self,
        account_number: str,
        meter_id: str,
        meter_type: str,
        start_date: datetime,
        end_date: datetime,
        progress_callback=None
    ) -> list[dict]:
        """Get consumption data for a meter over a date range.

        Args:
            account_number: The account number
            meter_id: The meter ID
            meter_type: Type of meter ('electricity' or 'gas')
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            progress_callback: Optional callback function(page_num, total_records) for progress updates

        Returns:
            List of consumption data records
        """

        # Format dates as ISO strings with timezone (required by API)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        if meter_type == "electricity":
            query = """
            query getElectricityConsumption($accountNumber: String!, $startDate: DateTime!, $after: String) {
                account(accountNumber: $accountNumber) {
                    electricityAgreements(active: true) {
                        meterPoint {
                            meters(includeInactive: false) {
                                id
                                consumption(
                                    startAt: $startDate
                                    grouping: HALF_HOUR
                                    timezone: "Europe/London"
                                    first: 100
                                    after: $after
                                ) {
                                    edges {
                                        node {
                                            startAt
                                            endAt
                                            value
                                            __typename
                                        }
                                        __typename
                                    }
                                    pageInfo {
                                        hasNextPage
                                        endCursor
                                        __typename
                                    }
                                    __typename
                                }
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
            }
            """
            operation = "getElectricityConsumption"
        else:  # gas
            query = """
            query getGasConsumption($accountNumber: String!, $startDate: DateTime!, $after: String) {
                account(accountNumber: $accountNumber) {
                    gasAgreements(active: true) {
                        meterPoint {
                            meters(includeInactive: false) {
                                id
                                consumption(
                                    startAt: $startDate
                                    grouping: HALF_HOUR
                                    timezone: "Europe/London"
                                    first: 100
                                    after: $after
                                ) {
                                    edges {
                                        node {
                                            startAt
                                            endAt
                                            value
                                            __typename
                                        }
                                        __typename
                                    }
                                    pageInfo {
                                        hasNextPage
                                        endCursor
                                        __typename
                                    }
                                    __typename
                                }
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
            }
            """
            operation = "getGasConsumption"

        # Paginate through all results
        consumption_data = []
        cursor = None
        has_next_page = True
        page_count = 0

        while has_next_page:
            page_count += 1

            # Call progress callback if provided
            if progress_callback:
                progress_callback(page_count, len(consumption_data))

            # Make the request with current cursor
            variables = {
                "accountNumber": account_number,
                "startDate": start_str
            }
            if cursor:
                variables["after"] = cursor

            result = await self._graphql_request(operation, query, variables)

            # Extract consumption data from the nested response
            if "data" not in result or "account" not in result["data"]:
                break

            agreements_key = "electricityAgreements" if meter_type == "electricity" else "gasAgreements"
            agreements = result["data"]["account"].get(agreements_key, [])

            for agreement in agreements:
                meter_point = agreement.get("meterPoint")
                if not meter_point:
                    continue

                meters = meter_point.get("meters", [])

                for meter in meters:
                    if meter and meter.get("id") == meter_id:
                        consumption_connection = meter.get("consumption")
                        if not consumption_connection:
                            has_next_page = False
                            break

                        edges = consumption_connection.get("edges", [])

                        # Extract nodes from edges and filter by end date
                        for edge in edges:
                            if not edge:
                                continue
                            node = edge.get("node")
                            if not node:
                                continue

                            # Filter by end date if we have interval data
                            interval_start = node.get("startAt", "")
                            if interval_start:
                                # Only include data up to the end date
                                if interval_start <= end_str:
                                    consumption_data.append(node)
                                else:
                                    # Past the end date, stop pagination
                                    has_next_page = False
                                    break

                        # Check pagination info
                        page_info = consumption_connection.get("pageInfo", {})
                        has_next_page = page_info.get("hasNextPage", False) and has_next_page
                        cursor = page_info.get("endCursor")

                        break

        return consumption_data
