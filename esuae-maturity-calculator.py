import streamlit as st
import pandas as pd
import numpy as np
import datetime
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="Elite Sport UAE Maturity Calculator", layout="wide")

# --- Header ---
logo_col, title_col = st.columns([1, 4])
logo_col.image("ESUAE Logo.png", width=100)
title_col.title("Elite Sport UAE Maturity Calculator")

# --- Data Loader ---
@st.cache_data
def load_data():
    xls = pd.ExcelFile("Maturation_calculator.xlsx")
    return {sheet: xls.parse(sheet) for sheet in xls.sheet_names}

data_sheets = load_data()
metric_df = data_sheets['Metric coefficients']
sa_df = data_sheets['SA']
error_df = data_sheets['Errors']

# --- Calculation Helper ---
def calculate_metrics(row):
    dob = pd.to_datetime(row['dob'])
    meas = pd.to_datetime(row.get('measurement_date', datetime.date.today()))
    age_years = (meas - dob).days / 365.25
    rounded_age = round(age_years * 2) / 2
    mom_in = row['mother_height_cm'] * 0.393701
    adj_mom_cm = (2.803 + 0.953 * mom_in) * 2.54
    dad_in = row['father_height_cm'] * 0.393701
    adj_dad_cm = (2.316 + 0.955 * dad_in) * 2.54
    midparent_cm = (adj_mom_cm + adj_dad_cm) / 2
    coeff = metric_df.loc[metric_df['Age'] == rounded_age].iloc[0]
    if row['sex'] == 'Male':
        h_coef, w_coef = coeff['Stature (in)'], coeff['Weight (lb)']
        m_coef, intercept = coeff['Midparent Stature (in)'], coeff['Beta']
    else:
        h_coef, w_coef = coeff['Height'], coeff['Weight']
        m_coef, intercept = coeff['Md parent'], coeff['Intersect']
    ph = h_coef * row['standing_height_cm'] + w_coef * row['body_mass_kg'] + m_coef * midparent_cm + intercept
    err = error_df.loc[error_df['Age'] == rounded_age].iloc[0]
    ci_val = err.get(0.9, err.get('0.9'))
    ci_low, ci_high = ph - ci_val, ph + ci_val
    pp = row['standing_height_cm'] / ph * 100
    pa_col = '%PAH Males' if row['sex'] == 'Male' else '%PAH females'
    ba = sa_df.loc[(sa_df[pa_col] - pp).abs().idxmin(), 'Age']
    ba_ca = ba - age_years
    timing = 'Early' if ba_ca > 1 else 'Late' if ba_ca <= -1 else 'On Time'
    if pp < 85:
        status = '<85% Pre-PHV'
    elif pp < 90:
        status = '85-90% Approaching-PHV'
    elif pp < 95:
        status = '90-95% Circa-PHV'
    else:
        status = '>95% Post-PHV'
    return pd.Series({
        'Athlete': row['athlete_name'],
        'Chronological Age (y)': round(age_years, 2),
        'Biological Age (y)': round(ba, 2),
        'BA-CA (y)': round(ba_ca, 2),
        'Height (cm)': row['standing_height_cm'],
        'Body Mass (kg)': row['body_mass_kg'],
        '% Predicted Height': round(pp, 1),
        'Predicted Adult Height (cm)': round(ph, 2),
        '90% CI Lower': f"{ci_low:.2f}",
        '90% CI Upper': f"{ci_high:.2f}",
        'Maturity Status': status,
        'Maturity Timing': timing
    })

# --- Sidebar Navigation & Inputs ---
view = st.sidebar.selectbox("Mode", ["Individual", "Group"])

if view == "Individual":
    st.sidebar.header("Individual Data Inputs")
    athlete_name = st.sidebar.text_input("Athlete Name", "John Smith")
    dob = st.sidebar.date_input("Date of Birth", datetime.date(2010,1,1), min_value=datetime.date(1900,1,1), max_value=datetime.date.today())
    meas_date = st.sidebar.date_input("Measurement Date", datetime.date.today(), min_value=dob, max_value=datetime.date.today())
    sex = st.sidebar.selectbox("Sex", ["Male","Female"], index=0)
    standing_height = st.sidebar.number_input("Standing Height (cm)", value=165.0)
    body_mass = st.sidebar.number_input("Body Mass (kg)", value=152.0)
    mother_height = st.sidebar.number_input("Mother's Height (cm)", value=167.0)
    father_height = st.sidebar.number_input("Father's Height (cm)", value=182.0)
    st.markdown("<h2 style='text-align:left'>Individual Athlete Maturity Estimation</h2>", unsafe_allow_html=True)
    if athlete_name:
        st.markdown(f"<h4 style='text-align:center'>{athlete_name}</h4>", unsafe_allow_html=True)
    st.write("")
    if all([athlete_name, standing_height, body_mass, mother_height, father_height]):
        df_row = pd.DataFrame([{  
            'athlete_name': athlete_name,
            'dob': dob, 'measurement_date': meas_date,
            'sex': sex, 'standing_height_cm': standing_height,
            'body_mass_kg': body_mass, 'mother_height_cm': mother_height,
            'father_height_cm': father_height
        }])
        res = calculate_metrics(df_row.iloc[0])
        for title, keys, cols in [
            ("Age Calculations", ['Chronological Age (y)','Biological Age (y)','BA-CA (y)'], 3),
            ("Anthropometry", ['Height (cm)','Body Mass (kg)'], 2),
            ("Maturity Assessment", ['% Predicted Height','Predicted Adult Height (cm)','90% CI Lower','90% CI Upper'], 4)
        ]:
            st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
            cols_objs = st.columns(cols)
            for col_obj, key in zip(cols_objs, keys):
                col_obj.markdown(f"<div style='text-align:center'><strong>{key}</strong><br>{res[key]}</div>", unsafe_allow_html=True)
        st.write("")
        b1,b2,b3 = st.columns([1,1,1])
        with b2:
            towb = BytesIO()
            pd.DataFrame([res]).to_excel(towb, index=False, engine='openpyxl')
            towb.seek(0)
            st.download_button("Download Results as Excel", data=towb, file_name=f"{athlete_name}_maturity.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        st.info("Please complete all sidebar inputs to view results.")

else:
    st.sidebar.header("Group Data Inputs")
    template = pd.DataFrame([{  
        'athlete_name': [''], 'dob': ['YYYY-MM-DD'], 'measurement_date': ['YYYY-MM-DD'],
        'sex': ['Male'], 'standing_height_cm': [''], 'body_mass_kg': [''],
        'mother_height_cm': [''], 'father_height_cm': ['']
    }])
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        template.to_excel(writer, index=False, sheet_name='Data')
    buf.seek(0)
    st.sidebar.markdown("1. Download Excel template below  ")
    st.sidebar.markdown("2. Populate file with athlete data in all columns  ")
    st.sidebar.markdown("3. Upload Excel file  ")
    upload = st.sidebar.file_uploader("Upload Dataset", type=["csv","xlsx"])
    st.sidebar.download_button("Download Excel Template", buf, file_name="template.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.header("Group Maturity Calculations")
    if upload:
        if upload.name.endswith('.xlsx'):
            df = pd.read_excel(upload, parse_dates=['dob','measurement_date'])
        else:
            df = pd.read_csv(upload, parse_dates=['dob','measurement_date'])
        results = df.apply(calculate_metrics, axis=1)
        st.subheader("Group Results")
        st.dataframe(results)
        bout = BytesIO()
        results.to_excel(bout, index=False, engine='openpyxl')
        bout.seek(0)
        st.download_button("Download Group Results as Excel", data=bout, file_name="batch_results.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
