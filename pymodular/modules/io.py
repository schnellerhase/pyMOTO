from pymodular import Module
import matplotlib.pyplot as plt
import numpy as np
from .assembly import DomainDefinition
import os


class PlotDomain2D(Module):
    def _prepare(self, domain: DomainDefinition, saveto: str = None, clim=None, cmap='gray_r'):
        self.clim = clim
        self.cmap = cmap
        self.domain = domain
        # assert domain.nz < 2, "Only for 2D or 1-element thick 2D models"
        self.fig = plt.figure()
        if saveto is not None:
            self.saveloc, self.saveext = os.path.splitext(saveto)
        else:
            self.saveloc, self.saveext = None, None
        self.iter = 0

    def _response(self, x):
        if self.domain.dim == 2:
            self.plot_2d(x)
        elif self.domain.dim == 3:
            self.plot_3d(x)
        else:
            raise NotImplementedError("Only 2D and 3D plots are implemented")
        assert len(self.fig.axes) > 0, "Figure must contain axes"
        self.fig.axes[0].set_title(f"{self.sig_in[0].tag}, Iteration {self.iter}")

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        if self.saveloc is not None:
            self.fig.savefig("{0:s}_{1:04d}{2:s}".format(self.saveloc, self.iter, self.saveext))

        self.iter += 1

    def plot_2d(self, x):
        data = x.reshape((self.domain.nx, self.domain.ny), order='F').T
        if hasattr(self, 'im'):
            self.im.set_data(data)
        else:
            ax = self.fig.add_subplot()
            self.im = ax.imshow(data, origin='lower', cmap=self.cmap)
            self.cbar = self.fig.colorbar(self.im, orientation='horizontal')
            ax.set(xlabel='x', ylabel='y')
            plt.show(block=False)
        clim = [np.min(data), np.max(data)] if self.clim is None else self.clim
        self.im.set_clim(vmin=clim[0], vmax=clim[1])

    def plot_3d(self, x):
        # prepare some coordinates, and attach rgb values to each
        ei, ej, ek = np.indices((self.domain.nx, self.domain.ny, self.domain.nz))
        els = self.domain.get_elemnumber(ei, ej, ek)
        densities = x[els]

        sel = densities > 0.4

        # combine the color components
        colors = np.zeros(sel.shape + (3,))
        colors[..., 0] = np.clip(1-densities, 0, 1)
        colors[..., 1] = np.clip(1-densities, 0, 1)
        colors[..., 2] = np.clip(1-densities, 0, 1)

        # and plot everything
        if len(self.fig.axes) ==0:
            from mpl_toolkits.mplot3d import Axes3D
            ax = self.fig.add_subplot(projection='3d')
            max_ext = max(self.domain.nx, self.domain.ny, self.domain.nz)
            ax.set(xlabel='x', ylabel='y', zlabel='z',
                   xlim=[(self.domain.nx-max_ext)/2, (self.domain.nx+max_ext)/2],
                   ylim=[(self.domain.ny-max_ext)/2, (self.domain.ny+max_ext)/2],
                   zlim=[(self.domain.nz-max_ext)/2, (self.domain.nz+max_ext)/2])
            plt.show(block=False)
        else:
            ax = self.fig.axes[0]

        if hasattr(self, 'fac'):
            for i, f in self.fac.items():
                f.remove()

        self.fac = ax.voxels(sel,
                  facecolors=colors,
                  edgecolors='k',#np.clip(2*colors - 0.5, 0, 1),  # brighter
                  linewidth=0.5)



class PlotIter(Module):
    def _prepare(self):
        self.iter = 0
        self.minlim = 1e+200
        self.maxlim = -1e+200

    def _response(self, *args):
        if not hasattr(self, 'fig'):
            self.fig, self.ax = plt.subplots(1, 1)

        if not hasattr(self, 'line'):
            self.line = []
            for i, s in enumerate(self.sig_in):
                self.line.append(None)
                self.line[i], = plt.plot([], [], '.', label=s.tag)

                self.ax.set_yscale('linear')
                self.ax.set_xlabel("Iteration")
                self.ax.legend()
                plt.show(block=False)

        for i, xx in enumerate(args):
            try:
                xadd = xx.reshape(xx.size)
                self.line[i].set_ydata(np.concatenate([self.line[i].get_ydata(), xadd]))
                self.line[i].set_xdata(np.concatenate([self.line[i].get_xdata(), self.iter*np.ones_like(xadd)]))
            except:
                xadd = xx
                self.line[i].set_ydata(np.append(self.line[i].get_ydata(), xadd))
                self.line[i].set_xdata(np.append(self.line[i].get_xdata(), self.iter))


            self.minlim = min(self.minlim, np.min(xadd))
            self.maxlim = max(self.maxlim, np.max(xadd))

        # dy = max((self.maxlim - self.minlim)/10, 1e-5 * self.maxlim)

        self.ax.set_xlim([-0.5, self.iter+0.5])
        if np.isfinite(self.minlim) and np.isfinite(self.maxlim):
            self.ax.set_ylim([self.minlim*0.95, self.maxlim*1.05])
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        # self.fig.savefig(self.filen)

        self.iter += 1

        return []