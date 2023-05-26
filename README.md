# A Precision Medicine Framework for Cerebrovascular Disease: Lessons Learned from a Study of Diagnostic Accuracy

This repository contains the code for a study entitled "A Precision Medicine Framework for Cerebrovascular Disease: Lessons Learned from a Study of Diagnostic Accuracy". 

A link to the manuscript of our study will be provided after publication. 

## Project Outline

The main focus of this study is the quantitative validation of a simulation-based precision medicine framework developed by our group, specifically designed for the evaluation of cerebral hemodynamics in patients suffering from Intracranial Arterial Disease (ICAD). The validation is based on comparison with Dynamic Susceptibility Contrast Magnetic Resonance Imaging (DSC-MRI).

The simulation framework manuscript can be accessed here: (https://biomedical-engineering-online.biomedcentral.com/articles/10.1186/s12938-021-00880-w)

## Repository Contents

The repository comprises two files that are instrumental in the analysis and interpretation of the study data:

1. `nipype_pipeline.py`: This file contains a post-processing pipeline that aids in the evaluation of the relative Mean Transit Time (relMTT) using DSC-MRI. The pipeline can also process perfusion maps of TTP, CBV, CBF, Tmax. The pipeline is designed using Nipype, an open-source project that provides a uniform interface to existing neuroimaging software.

2. `statistics.py`: This file includes the analysis of diagnostic accuracy which involves the calculation of sensitivity, specificity, and the Receiver Operating Characteristic (ROC) analysis incl. ROC curve figures.

## Repository Data Structure of nipype_pipeline.py

Here's a snapshot of the project data structure needed for nipype_pipeline.py. All files need to be provided in NIfTI format and gzipped. 

```
Repository
│
└───<Patient_ID1>
│   │   MPRAGE.nii.gz
│   │   DSC_Source.nii.gz
│   │   DSC_pgui_c_CBV.nii.gz
│   │   DSC_pgui_oSVD_MTT.nii.gz
│   │   DSC_pgui_oSVD_Tmax.nii.gz
│   │   DSC_pgui_parametric_CBF.nii.gz
│   │   DSC_pgui_parametric_CBV.nii.gz
│   │   DSC_pgui_parametric_MTT.nii.gz
│   │   DSC_pgui_parametric_Tmax.nii.gz
│   │   DSC_pgui_TPP.nii.gz
│   └───Masken_cut
│       │   ACA_contra_mask.nii.gz
│       │   ACA_ipsi_mask.nii.gz
│       │   hemi_contra_mask.nii.gz
│       │   hemi_ipsi_mask.nii.gz
│       │   MCA_contra_mask.nii.gz
│       │   MCA_ipsi_mask.nii.gz
│       │   PCA_contra_mask.nii.gz
│       │   PCA_ipsi_mask.nii.gz
│   
└───<Patient_ID2>
│   │   ...
│   └───Masken_cut
│       │   ...
│
...
```

### Data Files Descriptions

- **MPRAGE.nii.gz**: This file contains Magnetization Prepared Rapid Gradient Echo (MPRAGE) data, used as anatomical reference.

- **DSC_Source.nii.gz**: This is the source file for Dynamic Susceptibility Contrast (DSC) imaging.

- **DSC_pgui_c_CBV.nii.gz**: This file contains a perfusion map of cerebral blood volume (CBV) derived from DSC imaging.

- **DSC_pgui_oSVD_MTT.nii.gz**: This is a Mean Transit Time (MTT) map, calculated using oscillatory index singular value decomposition (oSVD) from DSC perfusion data.

- **DSC_pgui_oSVD_Tmax.nii.gz**: This file contains a map of the time to the maximum (Tmax), derived using oSVD from DSC data.

- **DSC_pgui_parametric_CBF.nii.gz**: This file holds a parametrically-derived cerebral blood flow (CBF) map based on DSC perfusion data.

- **DSC_pgui_parametric_CBV.nii.gz**: This is a parametrically-derived cerebral blood volume (CBV) map, derived from DSC perfusion data.

- **DSC_pgui_parametric_MTT.nii.gz**: This file contains a parametrically-derived Mean Transit Time (MTT) map from DSC data. 
 (This was used for the reference test of the validation study mentioned at the beginning of the readme)

- **DSC_pgui_parametric_Tmax.nii.gz**: This is a parametrically-derived time to the maximum (Tmax) map from DSC data.

- **DSC_pgui_TPP.nii.gz**: This file contains a Time to Peak (TPP) perfusion map, derived from DSC data.

### Mask Files Descriptions

- **Masken_cut/ACA_contra_mask.nii.gz**: This is a mask file representing the contralateral Anterior Cerebral Artery (

ACA) territory.

- **Masken_cut/ACA_ipsi_mask.nii.gz**: This mask file represents the ipsilateral Anterior Cerebral Artery (ACA) territory.

- **Masken_cut/hemi_contra_mask.nii.gz**: This mask file corresponds to the contralateral hemisphere.

- **Masken_cut/hemi_ipsi_mask.nii.gz**: This is a mask file for the ipsilateral hemisphere.

- **Masken_cut/MCA_contra_mask.nii.gz**: This mask represents the contralateral Middle Cerebral Artery (MCA) territory.

- **Masken_cut/MCA_ipsi_mask.nii.gz**: This is a mask file for the ipsilateral Middle Cerebral Artery (MCA) territory.

- **Masken_cut/PCA_contra_mask.nii.gz**: This mask file corresponds to the contralateral Posterior Cerebral Artery (PCA) territory.

- **Masken_cut/PCA_ipsi_mask.nii.gz**: This mask represents the ipsilateral Posterior Cerebral Artery (PCA) territory.

Ipsilateral refers to the arterial flow territories on the side of stenosis
Contralateral refers to healthy tissue of the arterial flow territories opposite to the side of stenosis 

## Repository Data Structure of statistics.py

The repository nedded for statistics.py is organized according to the output structure of `nipype_pipeline.py`. Here's a snapshot of the data structure:

```
<Run_Name>
│
└───25_DSC_parametric_MTT_reor_coreg_gm_VOI
│   └───<Subject_ID1>
│   │   └───_ACA_contra
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_ACA_ipsi
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_hemi_contra
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_hemi_ipsi
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_MCA_contra
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_MCA_ipsi
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_PCA_contra
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   │   └───_PCA_ipsi
│   │   │   │   DSC_pgui_parametric_MTT_reor_coreg.nii.gz
│   └───<Subject_ID2>
│   │   │   ...
│
└───<Simulation_Data>
    │   Side_of_stenosis.csv
    │   MAP70_MCAonly.csv
    │   MAP70.csv
    │   [Additional MAPs]
```

### Data Files Descriptions

- **25_DSC_parametric_MTT_reor_coreg_gm_VOI/<Subject_ID>/_*_*/DSC_pgui_parametric_MTT_reor_coreg.nii**: These files are the output of the nipype pipeline, specifically the DSC perfusion Mean Transit Time (MTT) maps that have been reoriented and coregistered. Each Subject_ID subdirectory contains separate folders for different vascular territories (ACA, MCA, PCA) and hemispheres (ipsi, contra).

## Simulation Data Files Descriptions

The `<Simulation_Data>` folder contains files associated with the simulation framework as described in Frey et al. (2021). The corresponding paper can be accessed here https://biomedical-engineering-online.biomedcentral.com/articles/10.1186/s12938-021-00880-w

- **Side_of_stenosis.csv**: This file documents the side of stenosis for each patient.

- **MAP70_MCAonly.csv**: This file contains the simulation results for a Mean Arterial Pressure (MAP) of 70mmHg only for MCA areas as can be generated by the simulation framework published by Frey et al (2021)

- **MAP70.csv**: This file contains simulation results for MAP 70mmHg of all territories 

- **[Additional MAPs].csv**: These are simulation results for different MAPs.

---


## Data accessability

The data used in this study is not openly available due to data privacy regulations. Access can be granted for qualified scientific requests. 

## Contact

If you have any queries regarding the project, feel free to reach out to jonas(dot)behland(at)charite(dot)de

Your contributions, suggestions, and feedback are most welcome. Feel free to open an issue or submit a pull request.

