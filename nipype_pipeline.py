import nipype.interfaces.fsl as fsl
from os.path import join as opj
import nipype.interfaces.freesurfer as fs
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline.engine import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Select
import os
import time
from nipype.interfaces.image import Reorient
from nipype import Node, Function
from nipype.interfaces.fsl import ImageMeants
from pathlib import Path
import pandas as pd


# start timer to calculate run time of the script
start = time.time()


############################## SET PATHS AND SUBS ##############################

# give your workflow a name
workflow_name = "run_01"
# path to patient data
experiment_dir = "/fast/users/..."
# path for data sink to save results
results_dir = "/fast/users/.../results"
# set number of CPU cores for multiple processing
cpus = 8
# name the subjects to run the script on
subject_list = ["PEG0005","PEG0006"]

# name workflow output files to be included for averaging in the final output .csv file
include_average_list=[
    "33_DSC_TTP_reor_coreg_gm_VOI_avg",
    "34_DSC_C_CBV_reor_coreg_gm_VOI_avg",
    "35_DSC_parametric_CBV_reor_coreg_gm_VOI_avg",
    "36_DSC_parametric_CBF_reor_coreg_gm_VOI_avg",
    "37_DSC_parametric_MTT_reor_coreg_gm_VOI_avg",
    "38_DSC_parametric_Tmax_reor_coreg_gm_VOI_avg",
    "39_DSC_oSVD_CBF_reor_coreg_gm_VOI_avg",
    "40_DSC_oSVD_MTT_reor_coreg_gm_VOI_avg",
    "41_DSC_oSVD_Tmax_reor_coreg_gm_VOI_avg",
    "42_DSC_sSVD_CBF_reor_coreg_gm_VOI_avg",
    "43_DSC_sSVD_MTT_reor_coreg_gm_VOI_avg",
    "44_DSC_sSVD_Tmax_reor_coreg_gm_VOI_avg"]


############################## NODE DEFINITIONS ################################

## SEARCH NODES ##
# nipype infosource node defines which subjects to include for select files node
infosource = Node(IdentityInterface(fields=["subject_id"]), name="infosource")
infosource.iterables = [("subject_id", subject_list)]
# dictionary of the files to select for this workflow
MPRAGE = opj(experiment_dir, "{subject_id}", "MPRAGE.nii.gz")
DSC_Source = opj(experiment_dir, "{subject_id}", "DSC_Source.nii.gz")
perfusion_imgs = opj(experiment_dir, "{subject_id}", "DSC_pgui*")
masks = opj(experiment_dir, "{subject_id}", "Masken_cut", "*mask.nii.gz")

# assing names to files in dictionary to call upon for wf.connect
templates = {
    "MPRAGE": MPRAGE,
    "DSC_Source": DSC_Source,
    "perf": perfusion_imgs,
    "masks": masks
            }
# define select file node to localize files
selectfiles = Node(SelectFiles(templates, base_directory=experiment_dir), name="selectfiles")


## CUSTOM NODE DSC_SOURCE FIRST TIMEPOINT EXTRACTION ##
def get_first_image_of_time_series(in_file):
    import nibabel as nib
    #extract path from DSC-source file name dropping the seven last digits '.nii.gz'
    save_path=in_file[:-7]+"_0.nii.gz"
    # load the image
    image = nib.load(in_file)
    # change shape of the data
    data=image.get_data()
    #subset the picture keeping x, y, z coordinates but dropping all other timepoints but 0
    data_1= data[:,:,:,0,0,0]
    #convert array to nifti format
    image_1 = nib.Nifti1Image(data_1, image.affine)
    #save the file in the subject folder without data sink
    nib.save(image_1, save_path)
    return save_path

# now we integrate the custom function as nipype custom node
extract_first_time_series_image = Node(Function(input_names=["in_file"],
                       output_names=["out_file"],
                       function=get_first_image_of_time_series),
              name='extract_timeseries')


## INTENSITY CORRECTION NODES/ FREESURFER NUC ##
correct = Node(fs.MNIBiasCorrection(), name="NUC")
correct.inputs.iterations = 6
correct.inputs.protocol_iterations = 1000
correct.inputs.distance = 50
correct_2 = correct.clone(name="NUC_2")


## SKULL STRIP NODE/ FSL BET ##
# set frac variables to fine-tune BET
skullstrip_MPRAGE = Node(fsl.BET(mask=True, output_type="NIFTI_GZ", robust=True, name="BETnode_MPRAGE", frac=0.6), name="BETnode_MPRAGE")
skullstrip_DSC = Node(fsl.BET(mask=True, output_type="NIFTI_GZ", robust=True, frac=0.5), name="BETnode_DSC")


## COREGISTRATION NODE/ MPRAGE AND DSC_SOURCE_0 ##
# Inter-modality registration using mutual info as cost function
reg = Node(fsl.FLIRT(),name="fsl_reg")
reg.inputs.cost="mutualinfo"


## LPS REORIENTATION NODES ##
# DSC_source is reference with RAI-orientation
# MPRAGE, perfusion maps, VOI masks need left posterior superior reorientation to match RAI
reorient_MPRAGE = Node(Reorient(orientation='LPS'), name="reorient_MPRAGE")
# Multiple input files per node require map nodes
reorient = MapNode(Reorient(orientation='LPS') ,iterfield=['in_file'], name="reorient_image")
reorient_VOI_masks = MapNode(Reorient(orientation='LPS') ,iterfield=['in_file'], name="reorient_VOI_masks")


## APPLY TRANSFORMATION MATRIX FOR COREGISTRATION ##
# 1) to perfusion maps
apptrans= MapNode(fsl.ApplyXFM(apply_xfm=True), name= "applytransforms",iterfield=['in_file'])

# 2) to DSC_Source_NUC_BET_mask
## APPLY TRANSFORM TO PERFUSION MAPS NODE ##
applytrans_dsc_mask= Node(fsl.ApplyXFM(apply_xfm=True), name= "applytrans_dsc_mask")


## GM/WM SEGMENTATION NODE/ FSL FAST ##
gmwmseg = Node(fsl.FAST(output_type='NIFTI_GZ', no_bias=True, segments=True), name="segmentation")


## SELECT GM MASK NODE ##
# fsl FAST segmentation node outputs 3 masks whitematter:1 grey matter:2 and csf:3 in a list called tissue class files.
# We want the 2. element in this list therefore use list[1].
select_gm_mask =  Node(Select(),name= "select_gm_mask")
select_gm_mask.inputs.index=1


## MASKING NODES/ FSL APPLY MASK ##
# Combination of DSC_mask and gm_mask with in_file=DSC_mask and mask_file=gm_mask selected from tissue class files
maskimage_dsc_gm = Node(fsl.ApplyMask(output_type='NIFTI_GZ'),name="maskimage_dsc_gm")

# Map node combining DSC_GM_masks with the 8 VOI_masks; in_file=VOI_masks (iterfield); mask_file=DSC_GM_mask
maskimage_dsc_gm_voi = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="maskimage_dsc_gm_voi",iterfield=["in_file"])

# Final mask (dsc, gm, voi) applied to DSC_param maps; both in_file and mask_file are iterfields
apply_maskimage = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="apply_maskimage",iterfield=["mask_file"])


## SELECT GM MASKED PERFUSION MAPS NODE ##
# this node selects the 12 greymatter-masked perfusion maps from the map node 'gm_mask' to allow for independent use in VOI_masking nodes
select_0 =  Node(Select(),name= "select_0")
select_0.inputs.index=0
select_1 =  Node(Select(),name= "select_1")
select_1.inputs.index=1
select_2 =  Node(Select(),name= "select_2")
select_2.inputs.index=2
select_3 =  Node(Select(),name= "select_3")
select_3.inputs.index=3
select_4 =  Node(Select(),name= "select_4")
select_4.inputs.index=4
select_5 =  Node(Select(),name= "select_5")
select_5.inputs.index=5
select_6 =  Node(Select(),name= "select_6")
select_6.inputs.index=6
select_7 =  Node(Select(),name= "select_7")
select_7.inputs.index=7
select_8 =  Node(Select(),name= "select_8")
select_8.inputs.index=8
select_9 =  Node(Select(),name= "select_9")
select_9.inputs.index=9
select_10 =  Node(Select(),name= "select_10")
select_10.inputs.index=10
select_11 =  Node(Select(),name= "select_11")
select_11.inputs.index=11


## VOI MASKING NODES ##
VOI_masking_0 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_0",iterfield=["mask_file"])
VOI_masking_1 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_1",iterfield=["mask_file"])
VOI_masking_2 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_2",iterfield=["mask_file"])
VOI_masking_3 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_3",iterfield=["mask_file"])
VOI_masking_4 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_4",iterfield=["mask_file"])
VOI_masking_5 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_5",iterfield=["mask_file"])
VOI_masking_6 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_6",iterfield=["mask_file"])
VOI_masking_7 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_7",iterfield=["mask_file"])
VOI_masking_8 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_8",iterfield=["mask_file"])
VOI_masking_9 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_9",iterfield=["mask_file"])
VOI_masking_10 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_10",iterfield=["mask_file"])
VOI_masking_11 = MapNode(fsl.ApplyMask(output_type='NIFTI_GZ'),name="VOI_masking_11",iterfield=["mask_file"])


## AVERAGING NODES/ IMAGE MEANTS ##
# calculates average intensity of a VOI for each perfusion map
avg_00 = MapNode(ImageMeants(),iterfield=["in_file","mask"],name="avg_00")
avg_01 = avg_00.clone(name="avg_01")
avg_02 = avg_00.clone(name="avg_02")
avg_03 = avg_00.clone(name="avg_03")
avg_04 = avg_00.clone(name="avg_04")
avg_05 = avg_00.clone(name="avg_05")
avg_06 = avg_00.clone(name="avg_06")
avg_07 = avg_00.clone(name="avg_07")
avg_08 = avg_00.clone(name="avg_08")
avg_09 = avg_00.clone(name="avg_09")
avg_10 = avg_00.clone(name="avg_10")
avg_11 = avg_00.clone(name="avg_11")

## AVERAGING NODES/ ImageStats for median/ 50th percentile (use -M for mean from non-zero values)
median = Node(ImageStats(op_string='-P 50',
             name="median"))
median.inputs.in_file = dir + "/DSC_pgui_parametric_MTT_reor_coreg.nii.gz"


############################## SUBSTITUTIONS ###################################
# substitutions are a list of 2-tuples and are carried out in the order in which they were entered. Use them to rename results.

substitutions = [
("_subject_id_", ""),
("_output", "_NUC"),
("_NUC_brain", "_NUC_BET"),
("_flirt", "_coreg"),
("_seg_0", "_seg_csf"),
("_seg_1", "_seg_gm"),
("_seg_2", "_seg_wm"),
("_lps", "_reor"),
("_masked", ""),


("VOI_masking_00", "ACA_contra"),
("VOI_masking_01", "ACA_ipsi"),
("VOI_masking_02", "MCA_contra"),
("VOI_masking_03", "MCA_ipsi"),
("VOI_masking_04", "PCA_contra"),
("VOI_masking_05", "PCA_ipsi"),
("VOI_masking_06", "hemi_contra"),
("VOI_masking_07", "hemi_ipsi"),

("VOI_masking_10", "ACA_contra"),
("VOI_masking_11", "ACA_ipsi"),
("VOI_masking_12", "MCA_contra"),
("VOI_masking_13", "MCA_ipsi"),
("VOI_masking_14", "PCA_contra"),
("VOI_masking_15", "PCA_ipsi"),
("VOI_masking_16", "hemi_contra"),
("VOI_masking_17", "hemi_ipsi"),

("VOI_masking_20", "ACA_contra"),
("VOI_masking_21", "ACA_ipsi"),
("VOI_masking_22", "MCA_contra"),
("VOI_masking_23", "MCA_ipsi"),
("VOI_masking_24", "PCA_contra"),
("VOI_masking_25", "PCA_ipsi"),
("VOI_masking_26", "hemi_contra"),
("VOI_masking_27", "hemi_ipsi"),

("VOI_masking_30", "ACA_contra"),
("VOI_masking_31", "ACA_ipsi"),
("VOI_masking_32", "MCA_contra"),
("VOI_masking_33", "MCA_ipsi"),
("VOI_masking_34", "PCA_contra"),
("VOI_masking_35", "PCA_ipsi"),
("VOI_masking_36", "hemi_contra"),
("VOI_masking_37", "hemi_ipsi"),

("VOI_masking_40", "ACA_contra"),
("VOI_masking_41", "ACA_ipsi"),
("VOI_masking_42", "MCA_contra"),
("VOI_masking_43", "MCA_ipsi"),
("VOI_masking_44", "PCA_contra"),
("VOI_masking_45", "PCA_ipsi"),
("VOI_masking_46", "hemi_contra"),
("VOI_masking_47", "hemi_ipsi"),

("VOI_masking_50", "ACA_contra"),
("VOI_masking_51", "ACA_ipsi"),
("VOI_masking_52", "MCA_contra"),
("VOI_masking_53", "MCA_ipsi"),
("VOI_masking_54", "PCA_contra"),
("VOI_masking_55", "PCA_ipsi"),
("VOI_masking_56", "hemi_contra"),
("VOI_masking_57", "hemi_ipsi"),

("VOI_masking_60", "ACA_contra"),
("VOI_masking_61", "ACA_ipsi"),
("VOI_masking_62", "MCA_contra"),
("VOI_masking_63", "MCA_ipsi"),
("VOI_masking_64", "PCA_contra"),
("VOI_masking_65", "PCA_ipsi"),
("VOI_masking_66", "hemi_contra"),
("VOI_masking_67", "hemi_ipsi"),

("VOI_masking_70", "ACA_contra"),
("VOI_masking_71", "ACA_ipsi"),
("VOI_masking_72", "MCA_contra"),
("VOI_masking_73", "MCA_ipsi"),
("VOI_masking_74", "PCA_contra"),
("VOI_masking_75", "PCA_ipsi"),
("VOI_masking_76", "hemi_contra"),
("VOI_masking_77", "hemi_ipsi"),

("VOI_masking_80", "ACA_contra"),
("VOI_masking_81", "ACA_ipsi"),
("VOI_masking_82", "MCA_contra"),
("VOI_masking_83", "MCA_ipsi"),
("VOI_masking_84", "PCA_contra"),
("VOI_masking_85", "PCA_ipsi"),
("VOI_masking_86", "hemi_contra"),
("VOI_masking_87", "hemi_ipsi"),

("VOI_masking_90", "ACA_contra"),
("VOI_masking_91", "ACA_ipsi"),
("VOI_masking_92", "MCA_contra"),
("VOI_masking_93", "MCA_ipsi"),
("VOI_masking_94", "PCA_contra"),
("VOI_masking_95", "PCA_ipsi"),
("VOI_masking_96", "hemi_contra"),
("VOI_masking_97", "hemi_ipsi"),

("VOI_masking_100", "ACA_contra"),
("VOI_masking_101", "ACA_ipsi"),
("VOI_masking_102", "MCA_contra"),
("VOI_masking_103", "MCA_ipsi"),
("VOI_masking_104", "PCA_contra"),
("VOI_masking_105", "PCA_ipsi"),
("VOI_masking_106", "hemi_contra"),
("VOI_masking_107", "hemi_ipsi"),

("VOI_masking_110", "ACA_contra"),
("VOI_masking_111", "ACA_ipsi"),
("VOI_masking_112", "MCA_contra"),
("VOI_masking_113", "MCA_ipsi"),
("VOI_masking_114", "PCA_contra"),
("VOI_masking_115", "PCA_ipsi"),
("VOI_masking_116", "hemi_contra"),
("VOI_masking_117", "hemi_ipsi"),

("avg_000", "ACA_contra"),
("avg_001", "ACA_ipsi"),
("avg_002", "MCA_contra"),
("avg_003", "MCA_ipsi"),
("avg_004", "PCA_contra"),
("avg_005", "PCA_ipsi"),
("avg_006", "hemi_contra"),
("avg_007", "hemi_ipsi"),

("avg_010", "ACA_contra"),
("avg_011", "ACA_ipsi"),
("avg_012", "MCA_contra"),
("avg_013", "MCA_ipsi"),
("avg_014", "PCA_contra"),
("avg_015", "PCA_ipsi"),
("avg_016", "hemi_contra"),
("avg_017", "hemi_ipsi"),

("avg_020", "ACA_contra"),
("avg_021", "ACA_ipsi"),
("avg_022", "MCA_contra"),
("avg_023", "MCA_ipsi"),
("avg_024", "PCA_contra"),
("avg_025", "PCA_ipsi"),
("avg_026", "hemi_contra"),
("avg_027", "hemi_ipsi"),

("avg_030", "ACA_contra"),
("avg_031", "ACA_ipsi"),
("avg_032", "MCA_contra"),
("avg_033", "MCA_ipsi"),
("avg_034", "PCA_contra"),
("avg_035", "PCA_ipsi"),
("avg_036", "hemi_contra"),
("avg_037", "hemi_ipsi"),

("avg_040", "ACA_contra"),
("avg_041", "ACA_ipsi"),
("avg_042", "MCA_contra"),
("avg_043", "MCA_ipsi"),
("avg_044", "PCA_contra"),
("avg_045", "PCA_ipsi"),
("avg_046", "hemi_contra"),
("avg_047", "hemi_ipsi"),

("avg_050", "ACA_contra"),
("avg_051", "ACA_ipsi"),
("avg_052", "MCA_contra"),
("avg_053", "MCA_ipsi"),
("avg_054", "PCA_contra"),
("avg_055", "PCA_ipsi"),
("avg_056", "hemi_contra"),
("avg_057", "hemi_ipsi"),

("avg_060", "ACA_contra"),
("avg_061", "ACA_ipsi"),
("avg_062", "MCA_contra"),
("avg_063", "MCA_ipsi"),
("avg_064", "PCA_contra"),
("avg_065", "PCA_ipsi"),
("avg_066", "hemi_contra"),
("avg_067", "hemi_ipsi"),

("avg_070", "ACA_contra"),
("avg_071", "ACA_ipsi"),
("avg_072", "MCA_contra"),
("avg_073", "MCA_ipsi"),
("avg_074", "PCA_contra"),
("avg_075", "PCA_ipsi"),
("avg_076", "hemi_contra"),
("avg_077", "hemi_ipsi"),

("avg_080", "ACA_contra"),
("avg_081", "ACA_ipsi"),
("avg_082", "MCA_contra"),
("avg_083", "MCA_ipsi"),
("avg_084", "PCA_contra"),
("avg_085", "PCA_ipsi"),
("avg_086", "hemi_contra"),
("avg_087", "hemi_ipsi"),

("avg_090", "ACA_contra"),
("avg_091", "ACA_ipsi"),
("avg_092", "MCA_contra"),
("avg_093", "MCA_ipsi"),
("avg_094", "PCA_contra"),
("avg_095", "PCA_ipsi"),
("avg_096", "hemi_contra"),
("avg_097", "hemi_ipsi"),


("avg_100", "ACA_contra"),
("avg_101", "ACA_ipsi"),
("avg_102", "MCA_contra"),
("avg_103", "MCA_ipsi"),
("avg_104", "PCA_contra"),
("avg_105", "PCA_ipsi"),
("avg_106", "hemi_contra"),
("avg_107", "hemi_ipsi"),


("avg_110", "ACA_contra"),
("avg_111", "ACA_ipsi"),
("avg_112", "MCA_contra"),
("avg_113", "MCA_ipsi"),
("avg_114", "PCA_contra"),
("avg_115", "PCA_ipsi"),
("avg_116", "hemi_contra"),
("avg_117", "hemi_ipsi"),
             ]


########################## DATASINK TO SAVE FILES ##############################

datasink = Node(DataSink(), name="datasink")
datasink.inputs.base_directory = results_dir
datasink.inputs.container = workflow_name + '_results' +""
datasink.inputs.substitutions = substitutions


############################ WORKFLOW CONNECTIONS ##############################

# define workflow
wf = Workflow(name=workflow_name)
wf.base_dir = experiment_dir


## HOW TO USE CONNECTIONS ##
# Selectfiles uses the dictionary of key strings in "template" defined above to select files.
# Datasink will save files in folders named with strings you define here
# All other NODES have "input" and "output" parameters as defined in the function. Those have to be taken from the Nipype documentation.


# describe how the nodes are connected to each other, specify input and output of each node
# output of every step is connected to the datasink
wf.connect([

    # subject ID subsetting
    (infosource, selectfiles, [("subject_id", "subject_id")]),

# MPRAGE pre-processing:
    # MPRAGEs are LPS reoriented to match other DSC files
    (selectfiles, reorient_MPRAGE, [("MPRAGE", "in_file")]),
    (reorient_MPRAGE, datasink, [("out_file", "01_MPRAGE_reor")]),
    
    # intensity normalization is performed (NUC)
    (reorient_MPRAGE, correct, [("out_file", "in_file")]),
    (correct, datasink, [("out_file", "02_MPRAGE_reor_NUC")]),

    # brain extraction (BET) gives out two outputs: (1) skull-stripped MPRAGE, (2) binary brain extraction mask 
    (correct, skullstrip_MPRAGE, [("out_file", "in_file")]),
    (skullstrip_MPRAGE, datasink, [("out_file", "03_MPRAGE_reor_NUC_BET")]),
    (skullstrip_MPRAGE, datasink, [("mask_file", "04_MPRAGE_reor_NUC_BET_mask")]),

    # MPRAGE grey-matter/ white-matter segmentation gives two outputs: (1) "tissue_class_files" for CSF, GM, and WM, (2) combined map of the three aforementioned 
    (skullstrip_MPRAGE, gmwmseg, [("out_file", "in_files")]),
    (gmwmseg, datasink, [("tissue_class_files", "05_MPRAGE_reor_NUC_BET_seg"),
                         ("tissue_class_map", "06_MPRAGE_reor_NUC_BET_seg_comb")]),
   
# DSC_Source pre-processing:
    # First timepoint of the DSC time series data is extracted using a custom_time_series_extraction_node
    (selectfiles, extract_first_time_series_image,  [("DSC_Source", "in_file")]),
    (extract_first_time_series_image, datasink, [("out_file", "07_DSC_Source_0")]),
    
    # intensity normalization is performed (NUC)
    (extract_first_time_series_image, correct_2, [("out_file", "in_file")]),
    (correct_2, datasink, [("out_file", "08_DSC_Source_0_NUC")]),

    # brain extraction (BET) gives out two outputs: (1) skull-stripped DSC_Source_0, (2) binary brain extraction mask 
    (correct_2, skullstrip_DSC, [("out_file", "in_file")]),
    (skullstrip_DSC, datasink, [("out_file", "09_DSC_Source_0_NUC_BET")]),
    (skullstrip_DSC, datasink, [("mask_file", "10_DSC_Source_0_NUC_BET_mask")]),

# Co-registration of DSC_Source_0 with MPRAGE
    # fsl_coreg is performed using 09_DSC_Source_0_NUC_BET base file and 03_MPRAGE_reor_NUC_BET as reference file 
    (skullstrip_MPRAGE, reg, [("out_file", "reference")]),
    (skullstrip_DSC, reg, [("out_file", "in_file")]),
    (reg, datasink, [("out_file", "11_DSC_Source_0_NUC_BET_coreg"), 
                     ("out_matrix_file", "12_DSC_Source_0_NUC_BET_coreg_matrix")]),

# Pre-processing of DSC-parametermaps: 
    # Parametermaps are LPS reoriented to match MPRAGE and other DSC files
    (selectfiles, reorient, [("perf", "in_file")]),
    (reorient, datasink, [("out_file", "13_DSC_parametermaps_reor")]),
    
    # The transformation matrix resulting from the co-registration of MPRAGE and DSC_Source_0 is applied to reoriented perfusion images
    # MPRAGE is used as reference image of the co-registration
    (reorient, apptrans, [("out_file", "in_file")]),
    (reg, apptrans, [("out_matrix_file", "in_matrix_file")]),
    (skullstrip_MPRAGE, apptrans, [("out_file", "reference")]),
    (apptrans, datasink, [("out_file", "14_DSC_parametermaps_reor_coreg")]),

# VOI mask Reorientation:
    # manual VOI masks are still in LPI orientation and need to be LPS reoriented 
    (selectfiles, reorient_VOI_masks, [("masks", "in_file")]),
    (reorient_VOI_masks, datasink, [("out_file", "16_VOI_masks_reor")]),

# PREPARATION FOR TRIPLE MASKS (GM, VOI, DSC)
# For the analysis three masks have to be combined before applying them to the perfusion parameter maps
# Step 1) DSC_mask (1x) + GM_mask (1x)
# Step 2) DSC_GM_mask (1x) + VOI_masks (8x)
# Step 3) apply DSC_GM_VOI_masks (8x) to 1/12 perfusion parameter map


# Step 1)
    # DSC_mask is co-registered to MPRAGE
    (skullstrip_DSC, applytrans_dsc_mask, [("mask_file", "in_file")]),
    (reg, applytrans_dsc_mask, [("out_matrix_file", "in_matrix_file")]),
    (skullstrip_MPRAGE, applytrans_dsc_mask, [("out_file", "reference")]),
    (applytrans_dsc_mask, datasink, [("out_file", "17_DSC_mask_coreg")]),

    # GM-masks have to be extracted from the three "tissue_class_files" of fsl FAST using a custom function
    # Only GM-areas of perfusion maps are considered for further analysis
    (gmwmseg, select_gm_mask, [("tissue_class_files", "inlist")]),

    # GM masking of DSC_mask
    # Combination of DSC_mask and gm_mask with in_file=DSC_mask and mask_file=gm_mask selected from tissue class files
    (applytrans_dsc_mask, maskimage_dsc_gm, [("out_file", "in_file")]),
    (select_gm_mask, maskimage_dsc_gm, [("out", "mask_file")]),
    (maskimage_dsc_gm, datasink, [("out_file", "18_Double_mask_DSC_GM")]),

# Step 2)
    # Map node combining DSC_GM_masks with the 8 VOI_masks; in_file=VOI_masks (iterfield); mask_file=DSC_GM_mask
    (reorient_VOI_masks, maskimage_dsc_gm_voi, [("out_file", "in_file")]),
    (maskimage_dsc_gm, maskimage_dsc_gm_voi, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, datasink, [("out_file", "19_Triple_mask_DSC_GM_VOI")]),

# Step 3)
    # Combined DSC_GM_VOI_masks (8x) are applied to the 12 perfusion parametermaps
    # First all 8 mask files are connected using iterfield
    (maskimage_dsc_gm_voi, VOI_masking_0, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_1, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_2, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_3, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_4, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_5, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_6, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_7, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_8, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_9, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_10, [("out_file", "mask_file")]),
    (maskimage_dsc_gm_voi, VOI_masking_11, [("out_file", "mask_file")]),

    # Each perfusion parameter map is selected from the list of 12 to be used separately
    # Note: this is only done because multiple iterfields did not work with this masking map node

    # select C_CBV from output list of apptrans
    (apptrans,select_0 , [("out_file","inlist")]),
    (select_0,VOI_masking_0, [("out", "in_file")]),

    # select TTP from output list of apptrans
    (apptrans, select_1, [("out_file", "inlist")]),
    (select_1, VOI_masking_1, [("out", "in_file")]),

    # select oSVD_CBF from output list of apptrans
    (apptrans, select_2, [("out_file", "inlist")]),
    (select_2, VOI_masking_2, [("out", "in_file")]),

    # select oSVD_MTT from output list of apptrans
    (apptrans, select_3, [("out_file", "inlist")]),
    (select_3, VOI_masking_3, [("out", "in_file")]),

    # select oSVD_Tmax from output list of apptrans
    (apptrans, select_4, [("out_file", "inlist")]),
    (select_4, VOI_masking_4, [("out", "in_file")]),

    # select parametric_CBF from output list of apptrans
    (apptrans, select_5, [("out_file", "inlist")]),
    (select_5, VOI_masking_5, [("out", "in_file")]),

    # select parametric_CBV from output list of apptrans
    (apptrans, select_6, [("out_file", "inlist")]),
    (select_6, VOI_masking_6, [("out", "in_file")]),

    # select parametric_MTT from output list of apptrans
    (apptrans, select_7, [("out_file", "inlist")]),
    (select_7, VOI_masking_7, [("out", "in_file")]),

    # select parametric_Tmax from output list of apptrans
    (apptrans, select_8, [("out_file", "inlist")]),
    (select_8, VOI_masking_8, [("out", "in_file")]),

    # select sSVD_CBF from output list of apptrans
    (apptrans, select_9, [("out_file", "inlist")]),
    (select_9, VOI_masking_9, [("out", "in_file")]),

    # select sSVD_MTT from output list of apptrans
    (apptrans, select_10, [("out_file", "inlist")]),
    (select_10, VOI_masking_10, [("out", "in_file")]),

    # select sSVD_Tmax from output list of apptrans
    (apptrans, select_11, [("out_file", "inlist")]),
    (select_11, VOI_masking_11, [("out", "in_file")]),

    # Triple masked perfusion images are safed to datasink
    (VOI_masking_0, datasink, [("out_file", "22_DSC_C_CBV_reor_coreg_gm_VOI")]),
    (VOI_masking_1, datasink, [("out_file", "21_DSC_TTP_reor_coreg_gm_VOI")]),
    (VOI_masking_2, datasink, [("out_file", "27_DSC_oSVD_CBF_reor_coreg_gm_VOI")]),
    (VOI_masking_3, datasink, [("out_file", "28_DSC_oSVD_MTT_reor_coreg_gm_VOI")]),
    (VOI_masking_4, datasink, [("out_file", "29_DSC_oSVD_Tmax_reor_coreg_gm_VOI")]),
    (VOI_masking_5, datasink, [("out_file", "24_DSC_parametric_CBF_reor_coreg_gm_VOI")]),
    (VOI_masking_6, datasink, [("out_file", "23_DSC_parametric_CBV_reor_coreg_gm_VOI")]),
    (VOI_masking_7, datasink, [("out_file", "25_DSC_parametric_MTT_reor_coreg_gm_VOI")]),
    (VOI_masking_8, datasink, [("out_file", "26_DSC_parametric_Tmax_reor_coreg_gm_VOI")]),
    (VOI_masking_9, datasink, [("out_file", "30_DSC_sSVD_CBF_reor_coreg_gm_VOI")]),
    (VOI_masking_10, datasink, [("out_file", "31_DSC_sSVD_MTT_reor_coreg_gm_VOI")]),
    (VOI_masking_11, datasink, [("out_file", "32_DSC_sSVD_Tmax_reor_coreg_gm_VOI")]),

# Average intensities of each VOI is extracted
    # Perfusion maps are used as separate in_files
    (VOI_masking_0, avg_00, [("out_file", "in_file")]),
    (VOI_masking_1, avg_01, [("out_file", "in_file")]),
    (VOI_masking_2, avg_02, [("out_file", "in_file")]),
    (VOI_masking_3, avg_03, [("out_file", "in_file")]),
    (VOI_masking_4, avg_04, [("out_file", "in_file")]),
    (VOI_masking_5, avg_05, [("out_file", "in_file")]),
    (VOI_masking_6, avg_06, [("out_file", "in_file")]),
    (VOI_masking_7, avg_07, [("out_file", "in_file")]),
    (VOI_masking_8, avg_08, [("out_file", "in_file")]),
    (VOI_masking_9, avg_09, [("out_file", "in_file")]),
    (VOI_masking_10, avg_10, [("out_file", "in_file")]),
    (VOI_masking_11, avg_11, [("out_file", "in_file")]),

    # Triple masks as additional input for averaging node
    (maskimage_dsc_gm_voi, avg_00, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_01, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_02, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_03, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_04, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_05, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_06, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_07, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_08, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_09, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_10, [("out_file", "mask")]),
    (maskimage_dsc_gm_voi, avg_11, [("out_file", "mask")]),

    # Average intensity values are saved in txt files
    (avg_00, datasink, [("out_file", "34_DSC_C_CBV_reor_coreg_gm_VOI_avg")]),
    (avg_01, datasink, [("out_file", "33_DSC_TTP_reor_coreg_gm_VOI_avg")]),
    (avg_02, datasink, [("out_file", "39_DSC_oSVD_CBF_reor_coreg_gm_VOI_avg")]),
    (avg_03, datasink, [("out_file", "40_DSC_oSVD_MTT_reor_coreg_gm_VOI_avg")]),
    (avg_04, datasink, [("out_file", "41_DSC_oSVD_Tmax_reor_coreg_gm_VOI_avg")]),
    (avg_05, datasink, [("out_file", "36_DSC_parametric_CBF_reor_coreg_gm_VOI_avg")]),
    (avg_06, datasink, [("out_file", "35_DSC_parametric_CBV_reor_coreg_gm_VOI_avg")]),
    (avg_07, datasink, [("out_file", "37_DSC_parametric_MTT_reor_coreg_gm_VOI_avg")]),
    (avg_08, datasink, [("out_file", "38_DSC_parametric_Tmax_reor_coreg_gm_VOI_avg")]),
    (avg_09, datasink, [("out_file", "42_DSC_sSVD_CBF_reor_coreg_gm_VOI_avg")]),
    (avg_10, datasink, [("out_file", "43_DSC_sSVD_MTT_reor_coreg_gm_VOI_avg")]),
    (avg_11, datasink, [("out_file", "44_DSC_sSVD_Tmax_reor_coreg_gm_VOI_avg")])

])

############################### RUN WORKFLOW ###################################

# Define number of CPUs used with n_procs
wf.run('MultiProc', plugin_args={'n_procs': cpus})

# Visualize the graph
wf.write_graph(graph2use='flat')

end = time.time()
print(end - start, "seconds")

################################# ANALYSIS #####################################

def create_a_directory(base_directory, directory_name_to_create):
    if not os.path.exists(base_directory + "/"+ directory_name_to_create):
        os.makedirs(base_directory + "/"+directory_name_to_create)
        print("....Created "+base_directory + "/" + directory_name_to_create)


def find_txts_and_corresponding_regions(directory, patient_name ,file="001.nii",  ):
    segmentation_strings=[]
    txts=[]
    for x, y, z in (os.walk(directory)):
        for item in z:
             if file in item:
                image_to_evaluate=os.path.join(x, item)
                #first leaves out(cuts) the filename of the path then
                cut = Path(image_to_evaluate).parent
                #gets the last element after /
                folder_name = os.path.basename(cut)
                #remove ground_truth from comparison
                # if ground_truth_folder_and_file_name not in folder_name:
                segmentation_strings.append(folder_name)
                if patient_name in image_to_evaluate:
                    txts.append(image_to_evaluate)
                #print(txts)
                dic = dict(zip(txts, segmentation_strings))
                print("Hi Jonas!", dic)
    return dic

#results directory
results_directory = results_dir+ "/" + workflow_name + '_results'
print("Here is the results directory: ", results_directory)
new_dict={}
dict_nice={}

#loops through patients and perfusion images
for patient in subject_list:
    content_all = []
    column_name_list=[]
    for perfusion_ID in include_average_list:
        #locates folder where txts are stored
        path=results_directory+"/"+perfusion_ID
        print("Here is the folder the txt file is stored", path)
        #finds all txt files in the path and saves them in a dictionary with their corresponding masks ACA, MCA etc
        dictionary=find_txts_and_corresponding_regions(path,patient,file="txt")
        print(dictionary)
        #reads the value in the text file and stores the values in a new dictionary
        for key, value in dictionary.items():
            f = open(key, "r")
            contents =f.read()
            content_all.append(float(contents))
            #value is the mask territory
            new_dict[patient + "_" + perfusion_ID+ value]=float(contents)
            column_name = perfusion_ID[3:] + value
            column_name = column_name.replace("_coreg_gm_VOI", "")
            column_name_list.append(column_name)
    dict_nice[patient]= content_all
    print(column_name_list)


df_nice=pd.DataFrame.from_dict(dict_nice,orient='index')
#creates dataframe from new_dict dictionary
df=pd.DataFrame.from_dict(new_dict,orient='index')
#renames the 0 column
df.rename(columns={0: "Average_VOI_intensity"}, inplace=True)
#creates a folder to save the csv file
create_a_directory(results_directory,"45_Results_VOI_avg")
df.to_csv(results_directory+"/"+ "45_Results_VOI_avg/all_averages.csv")

df_nice.columns = column_name_list
df_nice.to_csv(results_directory+"/"+ "45_Results_VOI_avg/all_averages_nice.csv")
