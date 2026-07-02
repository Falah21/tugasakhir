import pandas as pd
import streamlit as st

# GaitAnalysisData untuk data pemeriksaan pasien
class GaitAnalysisData:
    def __init__(self, data):
        self.df = pd.read_excel(data, sheet_name=[0, 1])
        self.suin = self.df[0]
        self.normkin = self.df[1].iloc[:, :31]

        self.cleaned_data = self.clean_data()
        self.normkin_processed = self.process_normkin()

        self.trial_info = self.extract_trial_info()
        self.subject_params = self.extract_subject_params()
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

    def extract_subject_params(self):
        return {
            "Subject Parameters": {
                "Subject Name": self.cleaned_data.iloc[3, 2],
                "Bodymass (kg)": self.cleaned_data.iloc[4, 2],
                "Height (mm)": self.cleaned_data.iloc[5, 2]
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
        return {
            "Norm Kinematics": {
                "Percentage of Gait Cycle": self.normkin_processed['Percentage of Gait Cycle'].values.tolist(),  # Convert to list
                "LPelvisAngles_X": self.normkin_processed["LPelvisAngles_X"].values.tolist(),
                "RPelvisAngles_X": self.normkin_processed["RPelvisAngles_X"].values.tolist(), 
                "LHipAngles_X": self.normkin_processed["LHipAngles_X"].values.tolist(),  
                "RHipAngles_X": self.normkin_processed["RHipAngles_X"].values.tolist(), 
                "LKneeAngles_X": self.normkin_processed["LKneeAngles_X"].values.tolist(), 
                "RKneeAngles_X": self.normkin_processed["RKneeAngles_X"].values.tolist(),
                "LAnkleAngles_X": self.normkin_processed["LAnkleAngles_X"].values.tolist(),  
                "RAnkleAngles_X": self.normkin_processed["RAnkleAngles_X"].values.tolist(),  
                "LFootProgressAngles_X": self.normkin_processed["LFootProgressAngles_X"].values.tolist(),  
                "RFootProgressAngles_X": self.normkin_processed["RFootProgressAngles_X"].values.tolist() 
            }
        }

    def to_dict(self):
        return {
            **self.trial_info,
            **self.subject_params,
            **self.body_measurements,
            **self.norm_kinematics
        }
