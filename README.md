# A Precision Medicine Framework for Cerebrovascular Disease: Lessons Learned from a Study of Diagnostic Accuracy

This repository contains the code for a study entitled "A Precision Medicine Framework for Cerebrovascular Disease: Lessons Learned from a Study of Diagnostic Accuracy". 

A link to the manuscript of our study will be provided after publication. 

## Project Outline

The main focus of this study is the quantitative validation of a simulation-based precision medicine framework developed by our group, specifically designed for the evaluation of cerebral hemodynamics in patients suffering from Intracranial Arterial Disease (ICAD). The validation is based on comparison with Dynamic Susceptibility Contrast Magnetic Resonance Imaging (DSC-MRI).

The simulation framework manuscript can be accessed here: (https://biomedical-engineering-online.biomedcentral.com/articles/10.1186/s12938-021-00880-w)

## Repository Contents

The repository comprises two files that are instrumental in the analysis and interpretation of the study data:

1. `nipype_pypeline.py`: This file contains a post-processing pipeline that aids in the evaluation of the relative Mean Transit Time (relMTT) using DSC-MRI. The pipeline can also process perfusion maps of TTP, CBV, CBF, Tmax. The pipeline is designed using Nipype, an open-source project that provides a uniform interface to existing neuroimaging software.

2. `statistics.py`: This file includes the analysis of diagnostic accuracy which involves the calculation of sensitivity, specificity, and the Receiver Operating Characteristic (ROC) analysis incl. ROC curve figures.

## Data accessability

The data used in this study is not openly available due to data privacy regulations. Access can be granted for qualified scientific requests. 

# Repository Data Structure

Here's a snapshot of the project data structure needed for nipype_pipeline.py:

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

## Data Files Descriptions

- **MPRAGE.nii.gz**: This file contains Magnetization Prepared Rapid Gradient Echo (MPRAGE) data, used for high-resolution T1-weighted brain imaging.

- **DSC_Source.nii.gz**: This is the source file for Dynamic Susceptibility Contrast (DSC) imaging, providing measures of cerebral blood flow and volume.

- **DSC_pgui_c_CBV.nii.gz**: This file contains a perfusion map of cerebral blood volume (CBV) derived from DSC imaging.

- **DSC_pgui_oSVD_MTT.nii.gz**: This is a Mean Transit Time (MTT) map, calculated using oscillatory index singular value decomposition (oSVD) from DSC perfusion data.

- **DSC_pgui_oSVD_Tmax.nii.gz**: This file contains a map of the time to the maximum of the residue function (Tmax), derived using oSVD from DSC data.

- **DSC_pgui_parametric_CBF.nii.gz**: This file holds a parametrically-derived cerebral blood flow (CBF) map based on DSC perfusion data.

- **DSC_pgui_parametric_CBV.nii.gz**: This is a parametrically-derived cerebral blood volume (CBV) map, derived from DSC perfusion data.

- **DSC_pgui_parametric_MTT.nii.gz**: This file contains a parametrically-derived Mean Transit Time (MTT) map from DSC data.

- **DSC_pgui_parametric_Tmax.nii.gz**: This is a parametrically-derived time to the maximum of the residue function (Tmax) map from DSC data.

- **DSC_pgui_TPP.nii.gz**: This file contains a Time to Peak (TPP) perfusion map, derived from DSC data.

## Mask Files Descriptions

- **Masken_cut/ACA_contra_mask.nii.gz**: This is a mask file representing the contralateral Anterior Cerebral Artery (

ACA) territory.

- **Masken_cut/ACA_ipsi_mask.nii.gz**: This mask file represents the ipsilateral Anterior Cerebral Artery (ACA) territory.

- **Masken_cut/hemi_contra_mask.nii.gz**: This mask file corresponds to the contralateral hemisphere.

- **Masken_cut/hemi_ipsi_mask.nii.gz**: This is a mask file for the ipsilateral hemisphere.

- **Masken_cut/MCA_contra_mask.nii.gz**: This mask represents the contralateral Middle Cerebral Artery (MCA) territory.

- **Masken_cut/MCA_ipsi_mask.nii.gz**: This is a mask file for the ipsilateral Middle Cerebral Artery (MCA) territory.

- **Masken_cut/PCA_contra_mask.nii.gz**: This mask file corresponds to the contralateral Posterior Cerebral Artery (PCA) territory.

- **Masken_cut/PCA_ipsi_mask.nii.gz**: This mask represents the ipsilateral Posterior Cerebral Artery (PCA) territory.


## Contact

If you have any queries regarding the project, feel free to reach out to jonas(dot)behland(at)charite(dot)de

Your contributions, suggestions, and feedback are most welcome. Feel free to open an issue or submit a pull request.

