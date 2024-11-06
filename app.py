# Using streamlit, create a web app that allows the user to upload a CSV file and diplay a Pandas DataFrame:
import streamlit as st
import pandas as pd
import io
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()


SMS_KEY = os.getenv("SMS_KEY")
# print(SMS_KEY)
SMS_KEY_TEST = SMS_KEY + "_test"
API_BASE = "https://textbelt.com/text"
COMPANY_NAME = "Colonial Realty Co."
FOOTER_TENANT_MSG = f"Thank you!\n{COMPANY_NAME}"
# tenant_msg = f'Hello $TENANT_NAME, this is {COMPANY_NAME}. Just a reminder, your rent of $TENANT_TENT for $TENANT_BUILDING is due on $TENANT_DUE_DATE. Please note a fees of $TENANT_LATE_FEE will be charged for any late payments. Thank you!'

# Rent Messages
RENT_MSG_1 = f"Hello \$TENANT_NAME, this is {COMPANY_NAME}\n Just a reminder, your rent for \$TENANT_BUILDING is due on \$TENANT_DUE_DATE. Please note a fee will be charged for any late payments. Thank you!"
RENT_MSG_2 = (
    f"Hi \$TENANT_NAME - Just a reminder, your rent is due on \$TENANT_DUE_DATE"
)
RENT_MSG_3 = f"Hello \$TENANT_NAME, this is {COMPANY_NAME}\n We have received your payment on-time. Thank you!"

# Maintainance Messages
MAINT_MSG_1 = f"Hi \$TENANT_NAME - Just a reminder, your maintenance will be conducted on \$TENANT_DUE_DATE"
MAINT_MSG_2 = f"Hi \$TENANT_NAME - Trash is collected on Monday and Sunday, thank you!"
MAINT_MSG_3 = f"Hi \$TENANT_NAME - Thank you for timely throwing out the trash!"


# Replace \$TENANT_NAME, \$TENANT_BUILDING, \$TENANT_DUE_DATE, \$TENANT_LATE_FEE in the message with the appropriate values:
def replace_placeholders(msg, tenantRow):
    if msg != None:
        return (
            msg.replace("\$TENANT_NAME", str(tenantRow["Name"]))
            .replace("\$TENANT_BUILDING", str(tenantRow["Building"]))
            .replace("\$TENANT_DUE_DATE", str(tenantRow["Due Date"]))
            .replace("\$TENANT_LATE_FEE", str(tenantRow["Late Fee"]))
        )
    else:
        return msg


# Dummy Tenant Row:
tenantRow = {
    "Name": "John Doe",
    "Building": "123 Main St",
    "Due Date": "2023-01-01",
    "Late Fee": "$10.00",
}

MESSAGE_TEMPLATES = [
    RENT_MSG_1,
    RENT_MSG_2,
    RENT_MSG_3,
    MAINT_MSG_1,
    MAINT_MSG_2,
    MAINT_MSG_3,
]


# Create a Test API Key function:
def test_api_key():
    resp = requests.post(
        API_BASE,
        {
            "phone": "7737154705",
            "message": "Hello world",
            "key": SMS_KEY_TEST,
        },
    )
    print(resp.json())
    if resp.json()["success"]:
        # Display a success message in streamlit:
        st.success("Key is valid")
    else:
        # Display an error message in streamlit:
        st.error("Key is not valid")


def send_sms_df(df, test=True, msg=None):
    if msg != None:
        for _, row in df.iterrows():
            if row["Send Rent SMS"]:
                send_sms(row, test, msg)
    else:
        # print error in streamlit
        error = st.error("No message provided")
        time.sleep(2)
        error.empty()


# Loop through the DataFrame and send SMS messages to the contacts:
def send_sms(tenantRow, test=True, msg=None):
    msg_updated = replace_placeholders(msg, tenantRow)
    sms_msg = f"{msg_updated}\n\n{FOOTER_TENANT_MSG}"
    print(sms_msg)
    resp = requests.post(
        API_BASE,
        {
            "phone": tenantRow["Contact"],
            "message": sms_msg,
            "key": test and SMS_KEY_TEST or SMS_KEY,
        },
    )
    time.sleep(1)
    print(resp.json())
    send_notifcation = st.empty()
    if resp.json()["success"]:
        # Display a success message in streamlit:
        send_notifcation = st.success(f"SMS sent to {tenantRow['Name']}")
    else:
        # Display an error message in streamlit:
        send_notifcation = st.error(f"SMS not sent to {tenantRow['Name']}")

    time.sleep(1)
    send_notifcation.empty()


st.set_page_config(page_title="Jannah SMS Test", layout="wide")
st.title("Jannah SMS Test")


uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
    # Load the CSV file into a pandas DataFrame and display it in streamlit with Contact as strings, Rent as integers, and Due Date as dates and "Send Rent SMS" as True or False:
    df = pd.read_csv(
        uploaded_file,
        dtype={
            "Contact": str,
            "Rent": int,
            "Building": str,
            "Late Fee": int,
            "Due Date": str,
            "Send Rent SMS": bool,
        },
    )
    # Load editable_df in streamlit session state:
    st.session_state["editable_df"] = st.data_editor(df)

st.session_state["test_api_key_button"] = st.button(
    "Test API Key", on_click=test_api_key
)

# Initialize editable_df in streamlit session state:
if "editable_df" not in st.session_state:
    st.session_state["editable_df"] = None
if "active_message" not in st.session_state:
    st.session_state["active_message"] = None

# Create tabs in streamlit for Rent and Maintenance messages and display them in streamlit, add buttons for each message as radio buttons in arrays to be sent using send_sms_df function:
if st.session_state["editable_df"] is not None:
    with st.expander("Message Templates"):
        active_message_radio = st.radio(
            "Message to Send",
            key="active_message_radio",
            options=MESSAGE_TEMPLATES,
            index=None,
        )
        st.session_state["active_message"] = active_message_radio

error = st.empty()
st.write(
    "SMS Message selected:",
    replace_placeholders(st.session_state["active_message"], tenantRow),
)

if "send_sms_button" not in st.session_state:
    st.session_state["send_sms_button"] = None

st.session_state["send_sms_button"] = st.button(
    "Send SMS",
    on_click=send_sms_df,
    disabled=st.session_state["editable_df"] is None,
    args=(st.session_state["editable_df"], True, st.session_state["active_message"]),
)


# Add a button to save the updated DataFrame back to the CSV file if the user has made any changes with the same name but new timestamp:
if st.session_state["editable_df"] is not None:
    if st.button("Save Updated SMS Contacts"):
        st.session_state["editable_df"].to_csv("JannahSMSTestContacts.csv", index=False)
        st.success("Changes saved to JannahSMSTestContacts.csv")
