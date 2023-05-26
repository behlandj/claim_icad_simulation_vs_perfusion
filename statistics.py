import nibabel as nib
import numpy as np
import pandas as pd
from datetime import datetime
import itertools
from sklearn import metrics
import matplotlib.pyplot as plt
import glob

#### DEFINITIONS ####
run_name = "run01"
directory = "C:/Users/..." + "/" + run_name
patient_list = ["PEG0005","PEG0006"]
#Statistics included in this analysis.This variable is used for generating column names for df (together with mask_list)
stats= ["_median"]
# If set to False, confusion matrices and ROC curve include mean and median.
graphics_median_only = True
# If load_csv = True, perfusion MTT data is extracted from .csv to df. This only has to be done once.
load_csv = True
save_results = False
save_as= "statistics"

#### DATA ####
#Specify which data should be used for analysis corresponding to folder name from nipype pipeline
file_folder = "25_DSC_parametric_MTT_reor_coreg_gm_VOI"
file = "DSC_pgui_parametric_MTT_reor_coreg.nii.gz"

#Load simulated perfusion from .csv
bp="MAP70_MCAonly"
#bp= ["MAP60", "MAP70", "MAP80", "MAP93"]
sim = pd.read_csv("C:/Users/.../"+bp+".csv", delimiter=";", index_col=0)

#Appends SoS (side of stenosis) data to the sim DataFrame ONLY if indices match. Left = 0, Right = 1
sos= pd.read_csv("C:/Users/.../Side_of_stenosis.csv", delimiter=";", index_col=0)
sim['Stenosis_L0_R1'] = sos["Stenosis_L0_R1"].values

#### THRESHOLDS FOR SIMULATION AND PERFUSION ####
# Set relMTT threshold to denote areas vulnerable to subsequent stroke;
# Source: Grubb RL, Derdeyn CP, Videen TO, Carpenter DA, Powers WJ. Relative mean transit time predicts subsequent
# stroke in symptomatic carotid occlusion. J Stroke Cerebrovasc Dis [Internet] 2016;25(6):1421–4. Available from:
# http://dx.doi.org/10.1016/j.jstrokecerebrovasdis.2015.12.041
relMTT_thr = 1.387

# Set simulation threshold to denote areas with vulnerable heamodynamics. This analysis assumes a lower threshold of
# cerebral autoregulation of 50mmHg; Source: Lassen NA. Cerebral Blood Flow and Oxygen Consumption in Man. Physiol
# Rev 1959;39(2):183–238.
sim_thr = 50

#### FUNCTIONS ####
def do_the_ROC (perf_vuln, sim_vuln):
    from sklearn import metrics
    fpr, tpr, thresholds = metrics.roc_curve(y_true=perf_vuln, y_score=sim_vuln, pos_label=True)
    roc_auc = metrics.auc(fpr,tpr)
    return fpr, tpr, thresholds, roc_auc

# Function takes pd.Series of vulnerabilities as input (i.e. perf_vuln: df['_MCA_median_vuln'], sim_vuln: sim['MCA_vuln'])
# and outputs confusion matrix and number of true_neg, false_pos, false_neg, true_pos
def create_confusion_matrix(perf_vuln, sim_vuln):
    from sklearn import metrics
    import matplotlib.pyplot as plt
    cm = metrics.confusion_matrix(y_true=perf_vuln, y_pred=sim_vuln, normalize=None)
    tn, fp, fn, tp = metrics.confusion_matrix(y_true=perf_vuln, y_pred=sim_vuln).ravel()
    #print("Confusion matrix for",perf_vuln.name[1:-5],":","\n","true_neg:",tn, "false_pos:",fp,"false_neg:",fn,"true_pos:",tp)
    sens = round(tp/(tp+fn), 4)
    spec = round(tn/(tn+fp), 4)
    accuracy = round((tn+tp)/(tn+tp+fn+fp),4)
    gmean = round(np.sqrt(sens * spec),4)
    f1 = round((2*tp)/((2*tp)+fp+fn),4)
    plot= 1
    data= pd.Series(data={'tn':tn, 'fp':fp, 'fn':fn, 'tp':tp, 'accuracy': accuracy, 'sens':sens, 'spec':spec, 'gmean': gmean, 'f1-score':f1}, name=perf_vuln.name[1:-5])
    return plot, data

# Function that takes the roc object as input (i.e. roc_MCA_median: 0:fpr, 1:tpr, 2:thresholds, 3:roc_auc)
# Returns the geometric mean of sensitivity and specificity, which helps to account for imbalanced data
# Also returns the simulation threshold (mmHg) with the highest gmean with corresponding optimal fpr, tpr
def opt_thr (roc, name):
    gmean = np.sqrt(roc[1] * (1 - roc[0]))
    # Find the optimal threshold
    index = np.argmax(gmean)
    thresholdOpt = round(roc[2][index], ndigits=4)
    gmeanOpt = round(gmean[index], ndigits=4)
    fprOpt = round(roc[0][index], ndigits=4)
    tprOpt = round(roc[1][index], ndigits=4)
    sensOpt = tprOpt
    specOpt = 1 - fprOpt
    print('\n___', name, '___')
    print('Best Simulation Threshold: {}mmHg with G-Mean: {}'.format(thresholdOpt, gmeanOpt))
    print('Sensitivity/TPR: \t {} \nSpecificity/1-FPR: \t {}'.format(fprOpt, tprOpt))
    return thresholdOpt, gmeanOpt, sensOpt, specOpt


#### Fill Perfusion DataFrame df ####
    #Loops to fill df with statistics data from the given nifti files
if (load_csv==True):
    df = pd.read_csv(directory + "/" + "mtt_mca.csv", na_values='--', delimiter=",", index_col=0)
    df = df.astype(float)
else:
    mask_list = ["_MCA_ipsi", "_MCA_contra"]
    columns = list(''.join(e) for e in itertools.product(mask_list, stats))
    df = pd.DataFrame(index=patient_list, columns=columns)

    #Use masking to only consider non-zero values of Nifti images
    for patient in patient_list:
        for mask in mask_list:
            path = directory + "/" + file_folder + "/" + patient + "/" + mask + "/" + file
            img = nib.load(path)
            img_data = img.get_fdata()
            m = np.ma.masked_equal(img_data, 0)
            median_value = np.ma.median(m)
            mean_value = np.ma.mean(m)
            df.loc[patient, mask + stats[0]] = median_value
            df.loc[patient, mask + stats[1]] = mean_value
            print(df)

    # Check if file with same name exists already. If not, save to .csv
        file_name = "mtt_mca.csv"
        files_present = glob.glob(file_name)
        if not files_present: df.to_csv(directory + "/" + file_name)


# Set index names of sim equal to those of df
# Might be prone to ID changes of only df or sim
sim.index = sim.index.str.replace('_','0')

#### Perfusion vulnerability analysis
#Create new Column with side-normalized values
df['_MCA_median_relMTT']=df._MCA_ipsi_median/df._MCA_contra_median
df['_MCA_mean_relMTT']=df._MCA_ipsi_mean/df._MCA_contra_mean

#Check if relMTT surpasses vulnerability threshold 1.387
df['_MCA_median_vuln'] = np.where(df._MCA_median_relMTT >= relMTT_thr, True, False)
df['_MCA_mean_vuln'] = np.where(df._MCA_mean_relMTT >= relMTT_thr, True, False)


#### Simulation vulnerability analysis
#Vulnerability of each region is saved as boolean value in columns 'ACA_vuln', 'MCA_vuln', 'PCA_vuln', 'hemi_vuln'

#Only take lower perfusion pressure of either M2 sup or M2 inf into consideration
sim['M2 R min'] = sim[['M2 sup R','M2 inf R']].min(axis=1)
sim['M2 L min'] = sim[['M2 sup L', 'M2 inf L']].min(axis=1)


# Account for side of stenosis
sim['M2_ipsi'] = np.where(sim['Stenosis_L0_R1'] == 0, sim['M2 L min'].values, sim['M2 R min'].values)

# Create columns for simulated vulnerabilities Sim_vuln according to simulation threshold
sim['MCA_vuln'] = np.where(sim['M2_ipsi'] < sim_thr, True, False)


#### Sensitivity and specificity analysis ####
#Create a results DataFrame to save all statistics
results = pd.DataFrame(columns=['tn', 'fp', 'fn', 'tp', 'accuracy', 'sens', 'spec', 'gmean', 'f1-score'])


if (graphics_median_only == True):
    cm_MCA_median = create_confusion_matrix(df['_MCA_median_vuln'], sim['MCA_vuln'])
    results.loc['MCA_median'] = cm_MCA_median[1]
    print('Summary of Confusion Matrices:\n', results)
else:
    cm_MCA_median = create_confusion_matrix(df['_MCA_median_vuln'],sim['MCA_vuln'])
    results.loc['MCA_median'] = cm_MCA_median[1]
    cm_MCA_mean = create_confusion_matrix(df['_MCA_mean_vuln'],sim['MCA_vuln'])
    results.loc['MCA_mean'] = cm_MCA_mean[1]
    print('Summary of Confusion Matrices:\n', results)


#### ROC Analysis

# Set parameters for all ROC plots
plt.figure(figsize=(5, 5))
plt.axline((0, 0), slope=1, color="grey", linestyle=(0, (5, 5)))
plt.ylabel('True Positive Rate')
plt.xlabel('False Positive Rate')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300

if (graphics_median_only == True):
    roc_MCA_median = do_the_ROC(1 - df['_MCA_median_vuln'], sim['M2_ipsi'])
    plt.plot(roc_MCA_median[0], roc_MCA_median[1], label="Frey et al. 2021, auc=" + str(roc_MCA_median[3])[0:5])
    plt.legend(loc=0)
    disp_roc_MCA_median = metrics.RocCurveDisplay(fpr=roc_MCA_median[0], tpr=roc_MCA_median[1],
                                                  roc_auc=roc_MCA_median[3], estimator_name='example estimator')

else:
    roc_MCA_median = do_the_ROC(1-df['_MCA_median_vuln'], sim['M2_ipsi'])
    roc_MCA_mean = do_the_ROC(1-df['_MCA_mean_vuln'], sim['M2_ipsi'])

    plt.plot(roc_MCA_median[0], roc_MCA_median[1], label="MCA median, auc="+str(roc_MCA_median[3])[0:5])
    plt.plot(roc_MCA_mean[0], roc_MCA_mean[1], label="MCA mean, auc="+str(roc_MCA_mean[3])[0:5])

    plt.legend(loc=0)

    disp_roc_MCA_median = metrics.RocCurveDisplay(fpr=roc_MCA_median[0], tpr=roc_MCA_median[1], roc_auc=roc_MCA_median[3], estimator_name = 'example estimator')
    disp_roc_MCA_mean = metrics.RocCurveDisplay(fpr=roc_MCA_mean[0], tpr=roc_MCA_mean[1], roc_auc=roc_MCA_mean[3], estimator_name = 'example estimator')


#### Measures for imbalanced data: G-mean, F1-Score ####
if (graphics_median_only == True):
    # Calculate the G-mean
    gmean_MCA_median = np.sqrt(roc_MCA_median[1] * (1 - roc_MCA_median[0]))
    # Find the optimal threshold
    gmeanOpt_MCA_median = opt_thr(roc_MCA_median, 'MCA_median')

else:
    # Calculate the G-mean
    gmean_MCA_median = np.sqrt(roc_MCA_median[1] * (1 - roc_MCA_median[0]))
    gmean_MCA_mean = np.sqrt(roc_MCA_mean[1] * (1 - roc_MCA_mean[0]))

    # Find the optimal threshold
    gmeanOpt_MCA_median = opt_thr(roc_MCA_median, 'MCA_median')
    gmeanOpt_MCA_mean = opt_thr(roc_MCA_mean, 'MCA_mean')

# Save statistics as .csv file using the current date
if (save_results==True):
    date = datetime.now().strftime("_%Y_%m_%d_%I_%M")
    df.to_csv(directory + "/" + save_as + "_" + date + "_dataframe.csv")
    sim.to_csv(directory + "/" + save_as + "_" + date + "_simulation.csv")
    results.to_csv(directory + "/" + save_as + "_" + date + "_results.csv")
    print("DataFrame", save_as + "_"+ date + ".csv", "created and saved to", directory)

plt.show()