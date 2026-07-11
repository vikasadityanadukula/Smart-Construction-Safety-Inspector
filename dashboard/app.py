import streamlit as st
import pandas as pd
import os
import json

#import requests
# ---------------- PAGE CONFIG ---------------- #

st.set_page_config(
    page_title="SafeSite AI",
    page_icon="🏗️",
    layout="wide"
)

# ---------------- DUMMY DATA ---------------- #
API_URL = "http://127.0.0.1:8000/dashboard"



def get_dashboard_data():

    try:
        # Get the SafeSiteAI project folder
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Full path to results.json
        RESULTS_FILE = os.path.join(BASE_DIR, "results.json")

        st.write("Reading from:", RESULTS_FILE)   # Debug

        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)

        st.write("JSON Loaded:", data)   # Debug

        return data

    except Exception as e:
        st.error(f"Error: {e}")

        return {
            "total_records": 0,
            "helmet_violations": 0,
            "vest_violations": 0,
            "danger_zone_entries": 0,
            "violations": []
        }


data = get_dashboard_data()


# ---------------- TITLE ---------------- #

st.title("🏗️ SafeSite AI")
st.subheader("Smart Construction Safety Inspector")

st.success("Dashboard Connected Successfully")

# ---------------- KPI CARDS ---------------- #

col1, col2, col3, col4 = st.columns(4)

col1.metric("👷 Workers", data["total_records"])
col2.metric("⛑ Helmet Violations", data["helmet_violations"])
col3.metric("🦺 Vest Violations", data["vest_violations"])
col4.metric("🚧 Danger Zone Entries", data["danger_zone_entries"])

st.divider()

# ---------------- FILE UPLOAD ---------------- #

uploaded_file = st.file_uploader(
    "Upload Construction Image or Video",
    type=["mp4","avi","mov","jpg","jpeg","png"]
)

if uploaded_file is not None:

    if uploaded_file.type.startswith("video"):

        st.header("📹 Live CCTV Feed")

        st.video(uploaded_file)

    elif uploaded_file.type.startswith("image"):

        st.header("🖼 Uploaded Image")

        st.image(uploaded_file,use_container_width=True)

st.divider()

 #---------------- LIVE ALERTS ---------------- 

st.header("🚨 Live Safety Alerts")

if len(data["violations"]) == 0:

    st.success("No Safety Violations")

else:

    for item in data["violations"]:

        if item["type"] == "Helmet Missing":

            st.error(
               f"⛑ Worker {item['worker_id']} - Helmet Missing ({item['time']})"
            )

        elif item["type"] == "Vest Missing":

            st.warning(
                f"🦺 Worker {item['worker_id']} - Vest Missing ({item['time']})"
           )

        elif item["type"] == "Danger Zone":

            st.error(
                f"🚧 Worker {item['worker_id']} entered Danger Zone ({item['time']})"
            )

st.divider()

# ---------------- BAR CHART ---------------- #

st.header("📊 Safety Violations Overview")

chart_data = pd.DataFrame({

    "Violation":[
        "Helmet",
        "Vest",
        "Danger Zone"
    ],

    "Count":[
        data["helmet_violations"],
        data["vest_violations"],
        data["danger_zone_entries"]
    ]

})

st.bar_chart(chart_data.set_index("Violation"))

st.divider()

# ---------------- LINE CHART ---------------- #

st.header("📈 Hourly Safety Trend")

trend = pd.DataFrame({

    "Hour":[
        "9 AM",
        "10 AM",
        "11 AM",
        "12 PM",
        "1 PM",
        "2 PM"
    ],

    "Violations":[
        1,
        2,
        3,
        2,
        4,
        3
    ]

})

st.line_chart(trend.set_index("Hour"))

st.divider()

# ---------------- VIOLATION TABLE ---------------- #

st.header("📋 Recent Violations")

table = pd.DataFrame(data["violations"])

st.dataframe(table,use_container_width=True)

st.divider()

# ---------------- PPE COMPLIANCE ---------------- #
st.header("🦺 PPE Compliance")

if data["total_records"] > 0:

    helmet = (data["total_records"] - data["helmet_violations"]) / data["total_records"]
    vest = (data["total_records"] - data["vest_violations"]) / data["total_records"]
    danger = (data["total_records"] - data["danger_zone_entries"]) / data["total_records"]

    st.write("Helmet Compliance")
    st.progress(helmet)

    st.write("Safety Vest Compliance")
    st.progress(vest)

    st.write("Danger Zone Compliance")
    st.progress(danger)

else:

    st.info("No records available yet.")



# ---------------- SYSTEM STATUS ---------------- #

st.header("🖥️ System Status")

c1,c2 = st.columns(2)

with c1:

    st.success("🟢 Camera Connected")

    st.success("🟢 Dashboard Online")

with c2:

    st.success("🟢 Backend Connected")

    st.success("🟢 AI Ready")

st.info("Last Updated : Just Now")

st.divider()

# ---------------- DOWNLOAD REPORT ---------------- #

#st.header("📄 Download Report")

#csv = table.to_csv(index=False)

#st.download_button(
 #   label="⬇ Download Safety Report",
  #  data=csv,
   # file_name="Safety_Report.csv",
    #mime="text/csv"
#)