import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Set the title of the app
st.set_page_config(
    page_title="Currency Exchange Rates Dashboard",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add a centered header
st.markdown(
    """
    <h1 style="text-align: center;">Currency Exchange Rates Dashboard</h1>
    """,
    unsafe_allow_html=True
)

# API base URL
API_BASE_URL = "http://api:8000"  

def rerun():
    st.rerun()

def sign_out():
    for key in st.session_state.keys():
        del st.session_state[key]
    rerun()

# Function to make authenticated requests
def make_request(endpoint, params=None, method="GET"):
    headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
    try:
        if method == "GET":
            response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, params=params)
        elif method == "POST":
            if endpoint == "/conversion":
                response = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, data=params)
            else:
                response = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=params)
        elif method == "PUT":
            response = requests.put(f"{API_BASE_URL}{endpoint}", headers=headers, json=params)
        elif method == "DELETE":
            response = requests.delete(f"{API_BASE_URL}{endpoint}", headers=headers, json=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            if "rate_limit_warning_shown" not in st.session_state:
                st.session_state.rate_limit_warning_shown = True
                st.warning("Rate limit exceeded. Please try again later.")
            return None
        elif response.status_code == 403:
            st.warning("Insufficient permissions")
            return None
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the API. Please try again later.")
        return None

# Sidebar for login
with st.sidebar:
    if "access_token" not in st.session_state:
        st.sidebar.title("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        login_button = st.sidebar.button("Login")

        if login_button and username and password:
            try:
                response = requests.post(f"{API_BASE_URL}/token", data={"username": username, "password": password})
                if response.status_code == 200:
                    st.session_state.access_token = response.json()["access_token"]
                    st.session_state.logged_in_username = username
                    st.sidebar.success("Logged in successfully...")
                    rerun()
                elif response.status_code == 429:
                    if "rate_limit_warning_shown" not in st.session_state:
                        st.session_state.rate_limit_warning_shown = True
                        st.warning("Rate limit exceeded. Please try again later.")
                else:
                    st.sidebar.error("Invalid username or password")
            except requests.exceptions.ConnectionError:
                st.sidebar.error("Failed to connect to the API. Please try again later.")
    else:
        headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        try:
            response = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                st.session_state.logged_in_username = user_data['username']
                st.sidebar.markdown(
                    f"""
                    <!-- Add bottom section with user details and sign-out -->
                    <div style="position: absolute; bottom: 10px; width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 5px 10px; background-color: #eaecee; color: white; font-family: Arial, sans-serif;">
                        <div style="display: flex; align-items: center; gap: 20px;">
                            <div style="font-size: 14px; color: #000000;">
                                {st.session_state['logged_in_username']} ({user_data['role']})
                            </div>
                        </div>
                        <div style="margin-left: auto; padding-left: 20px;">
                            <form action="?sign_out=true" method="get">
                                <button type="submit" style="padding: 5px 15px; background-color: #e74c3c; color: white; border: none; border-radius: 5px; font-size: 14px; cursor: pointer; font-family: Arial, sans-serif;">
                                    Sign Out
                                </button>
                            </form>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Real-time exchange rates in sidebar
                rates = make_request("/exchange-rates")
                if rates:
                    for rate in rates:
                        st.sidebar.markdown(
                            f"""
                            <div style="background-color: #f8f9f9; padding: 10px; border-radius: 5px; margin-bottom: 30px;">
                                <div style="font-size: 14px; font-weight: bold;">
                                    {rate['bank_name']}
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 14px;">
                                    <div>
                                        <div>Selling:</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #ff4b4b;">{rate['selling_rate']:.4f}</div>
                                    </div>
                                    <div>
                                        <div>Buying:</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #4caf50;">{rate['buying_rate']:.4f}</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px;">
                                    {rate['date']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # Create four columns in the sidebar with specific width distribution
                col1, col2, col3 = st.sidebar.columns([4, 3, 4])

                # Add the first image to the second column
                with col2:
                    st.image("logo/exchange.png", width=70)
                
                # Check for sign-out query parameter
                if st.query_params.get("sign_out"):
                    sign_out()
            else:
                st.sidebar.error("Failed to fetch user data. Please log in again.")
                sign_out()
        except requests.exceptions.ConnectionError:
            st.sidebar.error("Failed to connect to the API. Please try again later.")

# Check if the user is logged in
if "access_token" in st.session_state:
    col1, col2 = st.columns(2)
    
    with col1:
        # Currency conversion
        currencies = make_request("/currencies")
        if currencies:
            currency_options = [currency['code'] for currency in currencies]
            
            # Create two columns
            col11, col22 = st.columns(2)
            
            with col11:
                amount = st.number_input("Amount:", min_value=0, value=1)
                from_currency = st.selectbox("From Currency (e.g., USD):", options=currency_options, index=currency_options.index("USD"))
                to_currency_default = "THB" if from_currency == "USD" else "USD"
                to_currency = st.selectbox("To Currency (e.g., THB):", options=currency_options, index=currency_options.index(to_currency_default))
            
            with col22:
                params = {"amount": amount, "from_currency": from_currency, "to_currency": to_currency}
                conversion = make_request("/conversion", params=params, method="POST")
                if conversion:
                    currency_symbol = "$" if to_currency == "USD" else "฿"
                    st.markdown(
                        f"""
                        <div style="background-color: #f0f2f6; padding: 60px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 16px; font-weight: bold;">
                                {from_currency} to {to_currency}
                            </div>
                            <div style="font-size: 36px; font-weight: bold; color: #4caf50;">
                                {conversion['converted_amount']} {currency_symbol}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with col2:
        # Predictions
        predictions = make_request("/predictions")
        if predictions:
            df = pd.DataFrame(predictions['predictions'])
            
            fig = px.line(df, x="date", y="predicted_rate", title="Exchange Rate Predictions (Next 7 Days)", height=400)
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig)


    # Historical exchange rates
    st.subheader("Historical Exchange Rates (Last 30 Days)")
    historical_rates = make_request("/historical-rates")
    if historical_rates:
        df = pd.DataFrame(historical_rates)
        
        # Filter options
        rate_type = st.selectbox("Select Rate Type", ["Selling Rate", "Buying Rate"])
        rate_column = "selling_rate" if rate_type == "Selling Rate" else "buying_rate"
        
        fig = px.line(df, x="date", y=rate_column, color="bank_name", title=f"Historical {rate_type} (Last 30 Days)")
        st.plotly_chart(fig)
        
    col111, col222 = st.columns(2)
    with col111:
        # Supported banks
        st.markdown(
            """
            <h3 style="text-align: center;">Supported Banks</h3>
            """,
            unsafe_allow_html=True
        )
        banks = make_request("/banks")
        if banks:
            bank_options = [bank['name'] for bank in banks]
            selected_bank = st.selectbox("Select Bank", options=bank_options)
            selected_bank_data = next(bank for bank in banks if bank['name'] == selected_bank)
            # st.write(selected_bank_data)

            # Add bank
            st.subheader("Add Bank")
            new_bank_name = st.text_input("Bank Name")
            new_bank_code = st.text_input("Bank Code")
            if st.button("Add Bank"):
                new_bank = {"name": new_bank_name, "code": new_bank_code}
                make_request("/banks", params=new_bank, method="POST")
                st.success("Bank added successfully")
                rerun()

            # Update bank
            st.subheader("Update Bank")
            update_bank_name = st.text_input("Update Bank Name", value=selected_bank_data['name'])
            update_bank_code = st.text_input("Update Bank Code", value=selected_bank_data['code'])
            if st.button("Update Bank"):
                update_bank = {"name": update_bank_name, "code": update_bank_code}
                make_request(f"/banks/{selected_bank_data['id']}", params=update_bank, method="PUT")
                st.success("Bank updated successfully")
                rerun()

            # Delete bank
            if st.button("Delete Bank"):
                make_request(f"/banks/{selected_bank_data['id']}", method="DELETE")
                st.success("Bank deleted successfully")
                rerun()
            
    with col222:
        # Supported currencies
        st.markdown(
            """
            <h3 style="text-align: center;">Supported Currencies</h3>
            """,
            unsafe_allow_html=True
        )
        currencies = make_request("/currencies")
        if currencies:
            currency_options = [currency['code'] for currency in currencies]
            selected_currency = st.selectbox("Select Currency", options=currency_options)
            selected_currency_data = next(currency for currency in currencies if currency['code'] == selected_currency)
            # st.write(selected_currency_data)

            # Add currency
            st.subheader("Add Currency")
            new_currency_code = st.text_input("Currency Code")
            new_currency_name = st.text_input("Currency Name")
            if st.button("Add Currency"):
                new_currency = {"code": new_currency_code, "name": new_currency_name}
                make_request("/currencies", params=new_currency, method="POST")
                st.success("Currency added successfully")
                rerun()

            # Update currency
            st.subheader("Update Currency")
            update_currency_code = st.text_input("Update Currency Code", value=selected_currency_data['code'])
            update_currency_name = st.text_input("Update Currency Name", value=selected_currency_data['name'])
            if st.button("Update Currency"):
                update_currency = {"code": update_currency_code, "name": update_currency_name}
                make_request(f"/currencies/{selected_currency_data['id']}", params=update_currency, method="PUT")
                st.success("Currency updated successfully")
                rerun()

            # Delete currency
            if st.button("Delete Currency"):
                make_request(f"/currencies/{selected_currency_data['id']}", method="DELETE")
                st.success("Currency deleted successfully")
                rerun()
else:
    # Information to display before login
    st.markdown(
        """
        <div style="text-align: left;">
            <p>Features include:</p>
            <ul style="text-align: left; display: inline-block;">
                <li><strong>Real-time Exchange Rates:</strong> Get the latest exchange rates from various banks.</li>
                <li><strong>Currency Conversion:</strong> Convert amounts between different currencies using up-to-date rates.</li>
                <li><strong>Exchange Rate Predictions:</strong> View predictions for future exchange rates based on historical data.</li>
                <li><strong>Historical Exchange Rates:</strong> Analyze historical exchange rates for the past 30 days.</li>
                <li><strong>Manage Banks and Currencies:</strong> Add, update, and delete supported banks and currencies.</li>
            </ul>
            <p>Please log in to access the full features of the dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
