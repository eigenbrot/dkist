import matplotlib.pyplot as plt

import gwcs
from ndcube.mixins import NDCubePlotMixin
from sunpy.visualization.animator import ImageAnimator
from astropy.nddata.mixins.ndslicing import NDSlicingMixin

from dkist.wcs.slicer import GWCSSlicer

__all__ = ['DatasetPlotMixin', 'DatasetSlicingMixin']


class DatasetSlicingMixin(NDSlicingMixin):
    """
    A class to override the wcs slicing behavior of `astropy.nddata.mixins.NDSlicingMixin`.
    """
    def _slice(self, item):
        """
        Construct a set of keyword arguments to initialise a new (sliced)
        instance of the class. This method is called in
        `astropy.nddata.mixins.NDSlicingMixin.__getitem__`.

        This method extends the `~astropy.nddata.mixins.NDSlicingMixin` method
        to add support for ``missing_axis`` and ``extra_coords`` and overwrites
        the astropy handling of wcs slicing.
        """
        kwargs = super()._slice(item)

        wcs, missing_axis = self._slice_wcs_missing_axes(item)
        kwargs['wcs'] = wcs
        kwargs['missing_axis'] = missing_axis

        return kwargs

    # Implement this to stop it throwing a warning.
    def _slice_wcs(self, item):
        return

    def _slice_wcs_missing_axes(self, item):
        if self.wcs is None:
            return None, None
        if isinstance(self.wcs, gwcs.WCS):
            # Reverse the item so the pixel slice matches the cartesian WCS
            slicer = GWCSSlicer(self.wcs, copy=True, pixel_order=True)
            return slicer[item]
        return self.wcs[item], None


class DatasetPlotMixin(NDCubePlotMixin):  # pragma: no cover
    """
    Handle plotting operations for Dataset.
    """

    def _plot_3D_cube(self, image_axes=None, unit_x_axis=None, unit_y_axis=None,
                      axis_ranges=None, **kwargs):
        """
        Plots an interactive visualization of this cube using sliders to move through axes
        plot using in the image.
        Parameters other than data and wcs are passed to ImageAnimatorWCS, which in turn
        passes them to imshow.

        Parameters
        ----------
        image_axes: `list`
            The two axes that make the image.
            Like [-1,-2] this implies cube instance -1 dimension
            will be x-axis and -2 dimension will be y-axis.

        unit_x_axis: `astropy.units.Unit`
            The unit of x axis.

        unit_y_axis: `astropy.units.Unit`
            The unit of y axis.

        axis_ranges: `list` of physical coordinates for array or None
            If None array indices will be used for all axes.
            If a list it should contain one element for each axis of the numpy array.
            For the image axes a [min, max] pair should be specified which will be
            passed to :func:`matplotlib.pyplot.imshow` as extent.
            For the slider axes a [min, max] pair can be specified or an array the
            same length as the axis which will provide all values for that slider.
            If None is specified for an axis then the array indices will be used
            for that axis.
        """
        if not image_axes:
            image_axes = [-1, -2]
        i = ImageAnimator(self.data, image_axes=image_axes,
                          axis_ranges=axis_ranges, **kwargs)
        return i

    def _plot_2D_cube(self, axes=None, image_axes=None, **kwargs):
        """
        Plots a 2D image onto the current
        axes. Keyword arguments are passed on to matplotlib.

        Parameters
        ----------
        axes: `astropy.visualization.wcsaxes.core.WCSAxes` or `None`:
            The axes to plot onto. If None the current axes will be used.

        image_axes: `list`.
            The first axis in WCS object will become the first axis of image_axes and
            second axis in WCS object will become the second axis of image_axes.
            Default: ['x', 'y']
        """
        if not image_axes:
            image_axes = ['x', 'y']
        if axes is None:
            axes = plt.gca()
        plot = axes.imshow(self.data, **kwargs)
        return plot