import io
import pandas as pd
import streamlit as st

# GaitAnalysisData untuk Data Normal
class GaitAnalysisDataNormal:
    def __init__(self, content, usia, jenis_kelamin):
        try:
            self.df = pd.read_excel(io.BytesIO(content), sheet_name=[0, 1]) # Membaca file Excel
            self.suin = self.df[0]  # Lembar pertama untuk data mentah
            self.normkin = self.df[1].iloc[:, :31]  # Lembar kedua untuk normkin
        except Exception as e:
            st.error(f"Error reading the Excel file: {e}")
            return

        # Memproses data
        self.cleaned_data = self.clean_data()
        self.normkin_processed = self.process_normkin()
        self.trial_info = self.extract_trial_info()
        self.subject_params = self.extract_subject_params(usia, jenis_kelamin)
        self.body_measurements = self.extract_body_measurements()
        self.norm_kinematics = self.extract_norm_kinematics()

    def clean_data(self):
        cleaned_data = self.suin.dropna(how='all')
        cleaned_data.reset_index(drop=True, inplace=True)
        return cleaned_data

    def process_normkin(self):
        column_namesX = [col for col in self.normkin.columns if col.endswith('X')]
        normkin = self.normkin.loc[:, column_namesX]
        normkin.insert(0, "Percentage of Gait Cycle", self.df[1].iloc[:, 0].tolist())
        return normkin

    def extract_trial_info(self):
        return {
            "Trial Information": {
                "Trial Name": self.cleaned_data.iloc[1, 2]
            }
        }

    def extract_subject_params(self, usia, jenis_kelamin):
        bmi = (self.cleaned_data.iloc[4, 2])/((self.cleaned_data.iloc[5, 2]/1000)**2)
        bmi_class = (
            "Kurus Berat" if bmi < 17.0 else
            "Kurus Ringan" if bmi < 18.5 else
            "Normal" if bmi < 25.1 else
            "Gemuk Ringan" if bmi < 27.1 else
            "Gemuk Berat"
        )
        return {
            "Subject Parameters": {
                "Subject Name": self.cleaned_data.iloc[3, 2],
                "Age": usia,
                "Gender": jenis_kelamin.upper(),
                "Bodymass (kg)": self.cleaned_data.iloc[4, 2],
                "Height (mm)": self.cleaned_data.iloc[5, 2],
                "BMI": bmi,
                "BMI Classification": bmi_class
            }
        }

    def extract_body_measurements(self):
        return {
            "Body Measurements": {
                "Leg Length (mm)": {
                    "Left": self.cleaned_data.iloc[12, 2],
                    "Right": self.cleaned_data.iloc[12, 3]
                },
                "Knee Width (mm)": {
                    "Left": self.cleaned_data.iloc[13, 2],
                    "Right": self.cleaned_data.iloc[13, 3]
                },
                "Ankle Width (mm)": {
                    "Left": self.cleaned_data.iloc[14, 2],
                    "Right": self.cleaned_data.iloc[14, 3]
                }
            }
        }

    def extract_norm_kinematics(self):
        required_cols = [
        "Percentage of Gait Cycle", "LPelvisAngles_X", "RPelvisAngles_X",
        "LHipAngles_X", "RHipAngles_X", "LKneeAngles_X", "RKneeAngles_X",
        "LAnkleAngles_X", "RAnkleAngles_X", "LFootProgressAngles_X", "RFootProgressAngles_X"
    ]

        missing_cols = [col for col in required_cols if col not in self.normkin_processed.columns]
    
        if missing_cols:
            st.error(f"Incomplete kinematic data. Missing columns: {', '.join(missing_cols)}")
            st.stop()
        else:
            return {
                "Norm Kinematics": {
                    "Percentage of Gait Cycle": self.normkin_processed['Percentage of Gait Cycle'].tolist(),
                    "LPelvisAngles_X": self.normkin_processed["LPelvisAngles_X"].tolist(),
                    "RPelvisAngles_X": self.normkin_processed["RPelvisAngles_X"].tolist(),
                    "LHipAngles_X": self.normkin_processed["LHipAngles_X"].tolist(),
                    "RHipAngles_X": self.normkin_processed["RHipAngles_X"].tolist(),
                    "LKneeAngles_X": self.normkin_processed["LKneeAngles_X"].tolist(),
                    "RKneeAngles_X": self.normkin_processed["RKneeAngles_X"].tolist(),
                    "LAnkleAngles_X": self.normkin_processed["LAnkleAngles_X"].tolist(),
                    "RAnkleAngles_X": self.normkin_processed["RAnkleAngles_X"].tolist(),
                    "LFootProgressAngles_X": self.normkin_processed["LFootProgressAngles_X"].tolist(),
                    "RFootProgressAngles_X": self.normkin_processed["RFootProgressAngles_X"].tolist()
                }
            }

    def to_dict(self):
        return {
            **self.trial_info,
            **self.subject_params,
            **self.body_measurements,
            **self.norm_kinematics
        }
