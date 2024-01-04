# Extension of SAM-PT: automatic mask/point query initialization

This project is an extension of the original SAM-PT, to add automatic frame/point query initialization.

Two methods are available:

- **Ransac**: compares random points trajectories to distinguish foreground from background using Ransac algorithm.

- **YOLO**: Uses yolo to detect/segment the first frame objects.

To select one of those, modify `configs/model/sam_pt.yaml`. 
Set `no_mask_no_init_point` to `true` and `no_mask_no_init_point_method` to the desired method.

For more information, see the original [README](README_original.md).

