from functools import reduce

import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d as Axes3D
import numpy as np
from scipy.sparse import SparseEfficiencyWarning, lil_matrix
from scipy.sparse.linalg import spsolve

from chi2_grad_hess import _Chi2GradientHessian
from edge_odometry import EdgeOdometry
from pose_se2 import PoseSE2
from vertex import Vertex

EPS = np.finfo(float).eps


class Graph:
    def __init__(self, edges, vertices):

        self._edges = edges
        self._vertices = vertices

        self._chi2 = None
        self._gradient = None
        self._hessian = None

        self._link_edges()

    def _link_edges(self):
        
        """
        In this case, the id and index of the vertices are the same, so we can use the index as the id, 
        but in general, this is not the case, so we need to create a mapping between the two. For example, 
        the id of the first seen vertice might be 100, but its index is 0. index is the position of the 
        vertex in the list of vertices, while id is the id of the vertex

        """

        index_id_dict = {i: v.id for i, v in enumerate(self._vertices)} # vertex index to vertex id
        id_index_dict = {v_id: v_index for v_index, v_id in index_id_dict.items()} # vertex id to vertex index

        for v in self._vertices:
            v.index = id_index_dict[v.id]

        for e in self._edges:
            e.vertices = [self._vertices[id_index_dict[v_id]] for v_id in e.vertex_ids] # get the vertex object from the vertex id and assign it to the edge

    def add_edge(self, vertices, measurement, information):
        edge = EdgeOdometry(
            vertex_ids=vertices, information=information, estimate=measurement
        )
        self._edges.append(edge)
        self._link_edges()

    def add_vertex(self, id, pose):
        vertex = Vertex(vertex_id=id, pose=pose)
        self._vertices.append(vertex)
        self._link_edges()

    def get_pose(self, idx):
        vert = self._vertices[idx]
        return vert.pose

    def get_rt_matrix(self, idx):
        pose = self.get_pose(idx)
        return pose.get_rt_matrix()

    def calc_chi2(self):
        self._chi2 = sum((e.calc_chi2() for e in self._edges))[0, 0]
        return self._chi2

    def _calc_chi2_grad_hess(self):
        n = len(self._vertices)
        dim = len(self._vertices[0].pose.arr.squeeze())
        debug_var1 = (e.calc_chi2_gradient_hessian() for e in self._edges)
        debug_var2 = _Chi2GradientHessian(dim)
        
        chi2_gradient_hessian = reduce(
            _Chi2GradientHessian.update,
            debug_var1,
            debug_var2,
        )
        # breakpoint()
        self._chi2 = chi2_gradient_hessian.chi2[0, 0]

        # Populate the gradient vector
        self._gradient = np.zeros(n * dim, dtype=np.float64)
        for idx, contrib in chi2_gradient_hessian.gradient.items():
            self._gradient[idx * dim : (idx + 1) * dim] += contrib

        # Populate the Hessian matrix
        self._hessian = lil_matrix((n * dim, n * dim), dtype=np.float64) # lil_matrix is a list of lists sparse matrix
        for (row_idx, col_idx), contrib in chi2_gradient_hessian.hessian.items():
            self._hessian[
                row_idx * dim : (row_idx + 1) * dim, col_idx * dim : (col_idx + 1) * dim
            ] = contrib

            if row_idx != col_idx:
                # mirror the hessian along diagonal
                self._hessian[
                    col_idx * dim : (col_idx + 1) * dim,
                    row_idx * dim : (row_idx + 1) * dim,
                ] = np.transpose(contrib)

    def optimize(self, tol=1e-4, max_iter=40, fix_first_pose=True):
        n = len(self._vertices) # number of vertices
        dim = len(self._vertices[0].pose.arr.squeeze()) # dimension of the pose (here 3)

        prev_chi2_err = -1

        # For displaying the optimization progress
        print("\nIteration                chi^2        rel. change")
        print("---------                -----        -----------")

        for i in range(max_iter):
            self._calc_chi2_grad_hess()

            # only do this for the 2nd iteration onwards
            if i > 0:
                rel_diff = (prev_chi2_err - self._chi2) / (prev_chi2_err + EPS)
                print(f"{i:9} {self._chi2:20.4f} {-rel_diff:18.6f}")
                if (self._chi2 < prev_chi2_err) and rel_diff < tol:
                    return
            else:
                print(f"{i:9} {self._chi2:20.4f}")

            # Store the prev chi2 error
            prev_chi2_err = self._chi2
            if fix_first_pose:
                self._hessian[:dim, :] = 0.0
                self._hessian[:, :dim] = 0.0
                self._hessian[:dim, :dim] += np.eye(dim)
                self._gradient[:dim] = 0.0

            # run solver
            dx = spsolve(self._hessian.tocsr(), -self._gradient)

            # apply
            for v, dxi in zip(self._vertices, np.split(dx, n)):
                v.pose += PoseSE2.from_array(dxi)
        self.calc_chi2()
        rel_diff = (prev_chi2_err - self._chi2) / (prev_chi2_err + EPS)
        # breakpoint()
        print(f"{i:9} {self._chi2:20.4f} {-rel_diff:18.6f}")

    def plot(
        self,
        vertex_color="r",
        vertex_maker="o",
        vertex_markersize=3,
        edge_color="b",
        title=None,
    ):

        fig = plt.figure()

        for e in self._edges:
            e.plot(edge_color)
            # xy = np.array([self._vertices[v_indx].pose.position for v_indx in e.vertex_ids])
            # plt.plot(xy[:, 0], xy[:, 1], color=edge_color)

        for v in self._vertices:
            v.plot(vertex_color, vertex_maker, vertex_markersize)
        plt.savefig(f"{title}.png")
        plt.show()
