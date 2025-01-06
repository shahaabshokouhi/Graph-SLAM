import numpy as np

def warp2pi(angle_rad):
    """
    warps an angle in [-pi, pi]

    Args:
        angle_rad (float): An angle (in radians)

    Returns:
        float: The angle normalized to [-pi, pi]
    """
    if(angle_rad > np.pi):
        while(angle_rad > np.pi):
            angle_rad -= 2*np.pi
    elif (angle_rad < -np.pi):
        while(angle_rad < -np.pi):
            angle_rad += 2*np.pi
    return angle_rad

def upper_triangular_matrix_to_full_matrix(arr, n):

    triu0 = np.triu_indices(n, 0) # indices of the upper triangular part
    triu1 = np.triu_indices(n, 1) # indices of the upper triangular part excluding the diagonal
    tril1 = np.tril_indices(n, -1) # indices of the lower triangular part excluding the diagonal

    mat = np.zeros((n, n), dtype=np.float64)
    mat[triu0] = arr
    # filling the lower left-half with same values as right-half
    mat[tril1] = mat[triu1]
    return mat