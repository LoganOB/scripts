import pandas as pd
import numpy as np

def bioavailability(file):
  df = pd.read_csv(file, header=0)

  cols = ['Analyte', 'AUClast', 'Dose, mg/kg', 'Route']
  missing = [c for c in cols if c not in df.columns]
  if missing:
    raise ValueError(f"Missing required columns: {missing}")

  df = df[cols].copy()

  for c in ['Analyte', 'Route']:
    df[c] = df[c].astype(str).str.strip()
  df['Route'] = df['Route'].str.upper()

  df['AUClast/Dose']  = (df['AUClast'] / df['Dose, mg/kg'])
  df['Dose/AUClast']  = (df['Dose, mg/kg'] / df['AUClast'])
  df[['AUClast/Dose', 'Dose/AUClast']] = df[['AUClast/Dose', 'Dose/AUClast']].replace([np.inf, -np.inf], np.nan)

  per_ar = (
    df.groupby(['Analyte', 'Route'])['AUClast/Dose']
      .mean()
      .unstack('Route')
    )

  po = per_ar.get('PO')
  iv = per_ar.get('IV')

  F = (po / iv) * 100
  F = F.replace([np.inf, -np.inf], np.nan)

  df = df.merge(F.rename('%F'), left_on='Analyte', right_index=True, how='left')

  return df

bioavailability('pk-params.csv')  