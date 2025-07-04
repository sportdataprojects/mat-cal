import streamlit as st
import pandas as pd
import numpy as np
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Elite Sport UAE Maturity Calculator", layout="wide")

# --- Header with Logo and Title ---
logo_col, title_col = st.columns([1, 4])
logo_col.image("ESUAE Logo.png", width=100)
title_col.title("Elite Sport UAE Maturity Calculator")

# --- Data Loader (fixed file in same directory) ---
@st.cache_data
def load_data():
    xls = pd.ExcelFile("Maturation_calculator.xlsx")
    return {sheet: xls.parse(sheet) for sheet in xls.sheet_names}

# Load sheets
data_sheets = load_data()
metric_df = data_sheets['Metric coefficients']
sa_df = data_sheets['SA']
error_df = data_sheets['Errors']

# --- Main Tabs ---
tab1, tab2 = st.tabs(["Individual Input & Output", "Group Upload & Output"])

# Tab 1: Individual Entry
with tab1:
    st.header("Individual Maturation Prediction")
    col1, col2 = st.columns([1, 2])

    # Inputs
    with col1:
        athlete_name = st.text_input("Athlete Name")
        dob = st.date_input("Date of Birth", value=datetime.date(2010, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today())
        measurement_date = st.date_input("Measurement Date", value=datetime.date.today(), min_value=dob, max_value=datetime.date.today())
        sex = st.selectbox("Sex", ["Male", "Female"])
        standing_height = st.number_input("Standing Height (cm)", min_value=0.0)
        body_mass = st.number_input("Body Mass (kg)", min_value=0.0)
        mother_height = st.number_input("Mother's Height (cm)", min_value=0.0)
        father_height = st.number_input("Father's Height (cm)", min_value=0.0)

    # Outputs
    with col2:
        # Buffer space
        st.write("")
        st.write("")

        # Athlete name
        if athlete_name:
            st.markdown(f"**{athlete_name}**", unsafe_allow_html=True)

        if athlete_name and standing_height>0 and body_mass>0 and mother_height>0 and father_height>0:
            # Calculations
            age_years = round((measurement_date - dob).days / 365.25, 2)
            rounded_age = round(age_years * 2) / 2
            mother_inches = mother_height * 0.393701
            adj_mom_cm = (2.803 + 0.953 * mother_inches) * 2.54
            father_inches = father_height * 0.393701
            adj_dad_cm = (2.316 + 0.955 * father_inches) * 2.54
            midparent_cm = (adj_mom_cm + adj_dad_cm) / 2
            row = metric_df.loc[metric_df['Age'] == rounded_age].iloc[0]
            if sex == "Male":
                h_coef = row['Stature (in)']; w_coef = row['Weight (lb)']
                m_coef = row['Midparent Stature (in)']; intercept = row['Beta']
            else:
                h_coef = row['Height']; w_coef = row['Weight']
                m_coef = row['Md parent']; intercept = row['Intersect']
            pred_height = round(h_coef * standing_height + w_coef * body_mass + m_coef * midparent_cm + intercept, 2)
            err_row = error_df.loc[error_df['Age'] == rounded_age].iloc[0]
            ci_val = err_row.get(0.9, err_row.get('0.9'))
            ci_lower = round(pred_height - ci_val, 2); ci_upper = round(pred_height + ci_val, 2)
            percent_pred = round(standing_height / pred_height * 100, 1)
            pa_col = '%PAH Males' if sex == 'Male' else '%PAH females'
            bio_age = round(sa_df.loc[(sa_df[pa_col] - percent_pred).abs().idxmin(), 'Age'], 2)
            ba_ca = round(bio_age - age_years, 2)
            timing = 'Early' if ba_ca > 1 else 'Late' if ba_ca <= -1 else 'On Time'
            if percent_pred < 85:
                status = '<85% Pre-PHV'
            elif percent_pred < 90:
                status = '85-90% Approaching-PHV'
            elif percent_pred < 95:
                status = '90-95% Circa-PHV'
            else:
                status = '>95% Post-PHV'

            # Section 1: Age Calculations
            st.subheader("Age Calculations")
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Chronological Age (y)**\n{age_years:.2f}")
            c2.write(f"**Biological Age (y)**\n{bio_age:.2f}")
            c3.write(f"**BA-CA (y)**\n{ba_ca:.2f}")

            # Section 2: Anthropometry
            st.subheader("Anthropometry")
            c4, c5 = st.columns(2)
            c4.write(f"**Height (cm)**\n{standing_height:.1f}")
            c5.write(f"**Body Mass (kg)**\n{body_mass:.1f}")

            # Section 3: Maturity Assessment
            st.subheader("Maturity Assessment")
            c6, c7, c8 = st.columns(3)
            c6.write(f"**% Predicted Height**\n{percent_pred:.1f}%")
            c7.write(f"**Predicted Adult Height (cm)**\n{pred_height:.2f}")
            c8.write(f"**90% CI**\n{ci_lower:.2f}–{ci_upper:.2f}")

            # Section 4: Additional
            st.subheader("Additional")
            c9, c10 = st.columns(2)
            c9.write(f"**Maturity Status**\n{status}")
            c10.write(f"**Maturity Timing**\n{timing}")

            # Download CSV button centered
            st.write("")
            b1, b2, b3 = st.columns([1,1,1])
            with b2:
                csv = pd.DataFrame([{
                    'Athlete': athlete_name,
                    'DOB': dob,
                    'Measurement Date': measurement_date,
                    'Chronological Age (y)': age_years,
                    'Biological Age (y)': bio_age,
                    'BA-CA (y)': ba_ca,
                    'Height (cm)': standing_height,
                    'Body Mass (kg)': body_mass,
                    '% Predicted Height': percent_pred,
                    'Predicted Adult Height (cm)': pred_height,
                    '90% CI Lower': ci_lower,
                    '90% CI Upper': ci_upper,
                    'Maturity Status': status,
                    'Maturity Timing': timing
                }]).to_csv(index=False).encode('utf-8')
                st.download_button("Download Results as CSV", data=csv, file_name=f"{athlete_name}_maturity.csv", mime='text/csv')
        else:
            st.info("Please enter athlete name and all inputs to view results.")

# Tab 2: Group Upload & Output
with tab2:
    st.header("Group Data Upload & Batch Output")
    st.markdown("**Upload your Excel or CSV with these columns:** dob, sex, standing_height_cm, body_mass_kg, mother_height_cm, father_height_cm.")
    group_file = st.file_uploader("Upload .xlsx or .csv", type=["xlsx","csv"], key="group_upload")
    if group_file:
        if group_file.name.endswith('.xlsx'):
            df_group = pd.read_excel(group_file, sheet_name=0, parse_dates=['dob'])
        else:
            df_group = pd.read_csv(group_file, parse_dates=['dob'], dayfirst=True)
        st.subheader("Preview")
        st.dataframe(df_group)
        if st.button("Run Batch Calculations"):
            st.info("Batch processing not yet available.")
