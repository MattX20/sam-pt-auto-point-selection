import torch
import numpy as np
import cv2

def transform_and_sort_points(points, H):
    ones = torch.ones(points.shape[0], points.shape[1], 1)
    points_homogeneous = torch.cat([points[:, :, 1:], ones], dim=2)

    transformed_points = torch.matmul(H, points_homogeneous.permute(0, 2, 1))
    transformed_points = transformed_points.permute(0, 2, 1)

    transformed_points_2d = transformed_points[:, :, :2] / transformed_points[:, :, 2:]

    deviation = torch.norm(points[:, :, 1:] - transformed_points_2d, dim=2)

    sorted_indices = torch.argsort(deviation)
    sorted_points = points[torch.arange(points.shape[0])[:, None], sorted_indices]

    return sorted_points

def ransac_point_selector(trajectories, visibilities):
    """
    Selects points from trajectories using the RANSAC algorithm.

    Args:
        trajectories (torch.Tensor): The trajectories as float32 tensor
                                     of shape (num_frames, n_masks, n_points_per_mask, 2).
        visibilities (torch.Tensor): The visibilities as float32 tensor
                                     of shape (num_frames, n_masks, n_points_per_mask).

    Returns:
        positive_points (torch.Tensor): Inliers after applying the RANSAC algorithm.
        negative_points (torch.Tensor): Outliers after applying the RANSAC algorithm.
    """
    step = 24

    assert trajectories.shape[0] > step, "Insufficient frames for comparison."
    assert trajectories.shape[1] == 1, "Function is designed for one mask only."

    valid_points_mask = (visibilities[0, 0] == 1) & (visibilities[step, 0] == 1)
    trajectories_first_two_frames = trajectories[[0, step], 0, :]

    filtered_points_frame0 = trajectories_first_two_frames[0][valid_points_mask]
    filtered_points_frame1 = trajectories_first_two_frames[1][valid_points_mask]

    X = filtered_points_frame0.numpy()
    y = filtered_points_frame1.numpy()

    estimated_transform, inlier_mask = cv2.findHomography(X, y, cv2.RANSAC, 20)
    
    inlier_mask = inlier_mask.ravel().astype(bool)

    inliers = X[inlier_mask]

    outliers = X[~inlier_mask]

    if outliers.shape[0] == 0 :
        print("No foreground detected, random.")
        outliers = X[inlier_mask].copy()

    negative_points = torch.from_numpy(outliers).to(trajectories.dtype)
    negative_points = torch.cat((torch.zeros(negative_points.shape[0], 1), negative_points), dim=1).reshape(1, -1, 3)

    positive_points = torch.from_numpy(inliers).to(trajectories.dtype)
    positive_points = torch.cat((torch.zeros(positive_points.shape[0], 1), positive_points), dim=1).reshape(1, -1, 3)

    #H = torch.from_numpy(estimated_transform).float()
    #sorted_positive_points, sorted_negative_points = transform_and_sort_points(positive_points, H), transform_and_sort_points(negative_points, H) 

    return positive_points, negative_points

def yoloransac_point_selector(trajectories, visibilities, n_masks, n_points_per_mask):
    step = 24

    assert trajectories.shape[0] > step, "Insufficient frames for comparison."
    assert trajectories.shape[1] == 1, "Function is designed for one mask only."

    valid_points_mask = (visibilities[0, 0] == 1) & (visibilities[step, 0] == 1)
    trajectories_first_two_frames = trajectories[[0, step], 0, :]

    filtered_points_frame0 = trajectories_first_two_frames[0][valid_points_mask]
    filtered_points_frame1 = trajectories_first_two_frames[1][valid_points_mask]

    X = filtered_points_frame0.numpy()
    y = filtered_points_frame1.numpy()

    _, inlier_mask = cv2.findHomography(X, y, cv2.RANSAC, 20)
    
    inlier_mask = inlier_mask.ravel().astype(bool)
    outlier_mask = ~inlier_mask
    
    foreground_masks = []
    s = 0

    for i in range(n_masks):
        len_visible_points_mask_i = torch.sum(valid_points_mask[i*n_points_per_mask:(i+1)*n_points_per_mask])
        
        if len_visible_points_mask_i == 0:
            continue

        proportion_foreground = np.mean(outlier_mask[s:s+len_visible_points_mask_i])
        
        if proportion_foreground >= 0.5:
            foreground_masks.append(i)
        
        s += len_visible_points_mask_i

    return foreground_masks