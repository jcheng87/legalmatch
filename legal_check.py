import pandas as pd
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog

'''
file prereqs:
VC file must contain columns named: ['Vendor ID', 'Invoice Number']
ACM List must contain columns named: ['Vendor', 'Reference Nbr.']
Accruals files must contain named: ['Vendor ID', 'Invoice Number']
Reaccruals files must contain named: ['Vendor ID', 'Invoice Number']
Onit files must contain named: ['Vendor ID', 'Invoice Number']
'''

def legal_match():

    '''
    1) asks user for folder
    2) script classifies each file based on name
    3) takes vc confirm file and merges with other data sources
    '''

    CONFIRMS = ''
    ACMBILLS = []
    STAMPLI_ACCRUALS = []
    STAMPLI_REACCRUALS = []
    ONIT = []
    unknown_filetype = 0

    # prompts for folder
    root = tk.Tk()
    root.withdraw()
    dir_path = filedialog.askdirectory()
    files = os.listdir(dir_path)

    # classifies file types
    for file in files:
        filetype = file.split('_')[0]

        if filetype == 'vcconfirms':
            CONFIRMS = file
        elif filetype == 'acmbills':
            ACMBILLS.append(file)
        elif filetype == 'stmpaccruals':
            STAMPLI_ACCRUALS.append(file)
        elif filetype == 'stmpreaccruals':
            STAMPLI_REACCRUALS.append(file)
        elif filetype == 'onit':
            ONIT = file
        else:
            unknown_filetype+=1

    print('# of unknown files: ' + str(unknown_filetype))

    #VC Confirm file
    #['Vendor ID', 'Invoice Number]
    vc_df = pd.read_csv(os.path.join(dir_path,CONFIRMS),dtype={'Vendor ID':'object','Invoice Number':'object'})
    
    #Onit file
    #['Vendor ID', 'Invoice Number']
    onit_df = pd.read_csv(os.path.join(dir_path,ONIT),dtype={'Vendor ID':'object','Invoice Number':'object'})
    
    #confirm final df
    vc_final = vc_df.copy()
    vc_final['Amount'] = vc_final['Amount'].apply(lambda x: x.replace(',','')) #necessary step to convert to amount to float
    vc_final = vc_final.astype({'Amount':'float64'})

    # onit final df
    onit_final = onit_df.copy()

    #create check files for onit and vc
    onit_check = onit_df.copy()
    onit_check[ONIT] = True
    vc_check = vc_df.copy()
    vc_check[CONFIRMS] = True

    #merge onit check with vc_final and vc check with onit final
    vc_final = vc_final.merge(onit_check[['Vendor ID', 'Invoice Number', ONIT]], on=['Vendor ID','Invoice Number'], how='left') #merge onit with confirm df
    onit_final = onit_final.merge(vc_check[['Vendor ID', 'Invoice Number', CONFIRMS]], on=['Vendor ID','Invoice Number'], how='left') #merge vc with onit df
        
    # acm bills
    # ['Vendor','Vendor Ref.']
    for file in ACMBILLS:
        file_df = pd.read_csv(os.path.join(dir_path,file), dtype={'Vendor':'object','Vendor Ref.':'object'})
        file_df.rename(columns={'Vendor':'Vendor ID', 'Vendor Ref.':'Invoice Number'}, inplace=True)
        file_df[file] = True

        #merge with final dfs
        vc_final = vc_final.merge(file_df[['Vendor ID','Invoice Number', file]], on=['Vendor ID','Invoice Number'], how='left')
        onit_final = onit_final.merge(file_df[['Vendor ID','Invoice Number', file]], on=['Vendor ID','Invoice Number'], how='left')


    # stampli accruals
    for file in STAMPLI_ACCRUALS:
        file_df = pd.read_csv(os.path.join(dir_path,file),dtype={'Vendor ID':'object','Invoice Number':'object'})
        file_df[file] = True

        #merge with confirm df
        vc_final = vc_final.merge(file_df[['Vendor ID','Invoice Number', file]], on =['Vendor ID','Invoice Number'], how='left')
        onit_final = onit_final.merge(file_df[['Vendor ID','Invoice Number', file]], on=['Vendor ID','Invoice Number'], how='left')


    # stampli reaccruals
    for file in STAMPLI_REACCRUALS:
        file_df = pd.read_csv(os.path.join(dir_path,file),dtype={'Max. GL Rerefence Number':'object', 'Invoice Number':'object'})
        file_df[file] = True

        #rename columns in ACM bills
        file_df = file_df.rename(columns={'Max. GL Rerefence Number':'Vendor ID'})

        #merge with confirm df
        vc_final = vc_final.merge(file_df[['Vendor ID','Invoice Number', file]], on=['Vendor ID','Invoice Number'], how='left')
        onit_final = onit_final.merge(file_df[['Vendor ID','Invoice Number', file]], on=['Vendor ID','Invoice Number'], how='left')


    #count times invoice appears in source docs and return if they're accrued
    vc_all_columns = ACMBILLS + STAMPLI_ACCRUALS +STAMPLI_REACCRUALS + [ONIT]
    onit_all_columns = ACMBILLS + STAMPLI_ACCRUALS +STAMPLI_REACCRUALS + [CONFIRMS]

    #count
    vc_final['Count'] = 0
    onit_final['Count'] = 0

    for col in vc_all_columns:
        vc_final['Count'] = vc_final['Count'] + vc_final[col].notna()

    for col in onit_all_columns:
        onit_final['Count'] = onit_final['Count'] + onit_final[col].notna()
    
    #accrued?
    vc_final['Accrued?'] = vc_final['Count']>0
    onit_final['Accrued?'] = onit_final['Count']>0

    #create pivot for vc_final
    vc_final_pv= vc_final.pivot_table(index='Vendor Name', columns = ['Unbilled/Unpaid','Accrued?','Currency'], values='Amount', aggfunc=np.sum, margins=True)
    onit_final_pv= onit_final.pivot_table(index='ACM Vendor Name', columns = ['Accrued?'], values='Invoice Total (USD)', aggfunc=np.sum, margins=True)

    return {'vc_final':vc_final,'onit_final':onit_final,'vc_final_pv':vc_final_pv, 'onit_final_pv':onit_final_pv}
