import os

import asdf
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.io import fits
from astropy.io.fits.hdu.base import BITPIX2DTYPE
from astropy.modeling.models import (Shift, Multiply, AffineTransformation2D, Pix2Sky_TAN,
                                     RotateNative2Celestial, Linear1D)
from gwcs.lookup_table import LookupTable
from asdf.tags.core.external_reference import ExternalArrayReference


__all__ = ['make_asdf', 'time_model_from_date_obs', 'linear_time_model', 'linear_spectral_model',
           'spatial_model_from_quantity', 'spatial_model_from_header', 'references_from_filenames']


def references_from_filenames(filenames, array_shape, hdu_index=0, relative_to=None):
    """
    Given an array of paths to FITS files create a set of nested lists of
    `asdf.external_reference.ExternalArrayReference` objects with the same
    shape.

    Parameters
    ----------

    filenames : `numpy.ndarray`
        An array of filenames, in numpy order for the output array (i.e. ``.flat``)

    array_shape : `tuple`
        The desired output shape of the reference array. (i.e the shape of the
        data minus the HDU dimensions.)

    hdu_index : `int` (optional, default 0)
        The index of the HDU to reference. (Zero indexed)

    relative_to : `str` (optional)
        If set convert the filenames to be relative to this path.
    """

    filenames = np.asanyarray(filenames)
    reference_array = np.empty(array_shape, dtype=object)
    if filenames.size != reference_array.size:
        raise ValueError("Not enough filenames supplied for array_shape")

    for i, filepath in enumerate(filenames.flat):
        with fits.open(filepath) as hdul:
            hdu = hdul[hdu_index]
            dtype = BITPIX2DTYPE[hdu.header['BITPIX']]
            # hdu.shape is already in Python order
            shape = tuple(hdu.shape)

            # Convert paths to relative paths
            relative_path = filepath
            if relative_to:
                relative_path = os.path.relpath(filepath, relative_to)

            reference_array.flat[i] = ExternalArrayReference(
                relative_path, hdu_index, dtype, shape)

    return reference_array.tolist()


def spatial_model_from_header(header):
    """
    Given a FITS compliant header with CTYPE1,2 as HPLN, HPLT return a
    `~astropy.modeling.CompositeModel` for the transform.

    The ordering of ctype1 and ctype2 should be LON, LAT
    """

    assert header['CTYPE1'].startswith("HPLN")
    assert header['CTYPE2'].startswith("HPLT")

    crpix1, crpix2 = (header['CRPIX1'], header['CRPIX2']) * u.pixel
    crval1, crval2 = (header['CRVAL1'], header['CRVAL2']) * u.arcsec
    cdelt1, cdelt2 = (header['CDELT1'], header['CDELT2']) * (u.arcsec/u.pix)
    pc = np.matrix([[header['PC1_1'], header['PC1_2']],
                    [header['PC2_1'], header['PC2_2']]])

    return spatial_model_from_quantity(crpix1, crpix2, cdelt1, cdelt2, pc, crval1, crval2)


def spatial_model_from_quantity(crpix1, crpix2, cdelt1, cdelt2, pc, crval1, crval2):
    """
    Given quantity representations of a HPLx FITS WCS return a model for the
    spatial transform.

    The ordering of ctype1 and ctype2 should be LON, LAT
    """
    shiftu = Shift(-crpix1) & Shift(-crpix2)
    scale = Multiply(cdelt1) & Multiply(cdelt2)
    rotu = AffineTransformation2D(pc, translation=(0, 0)*u.arcsec)
    tanu = Pix2Sky_TAN()  # lon, lat
    skyrotu = RotateNative2Celestial(crval1, crval2, 180*u.deg)
    return shiftu | scale | rotu | tanu | skyrotu


@u.quantity_input
def linear_spectral_model(spectral_width: u.nm, reference_val: u.nm):
    """
    A linear model in a spectral dimension. The reference pixel is always 0.
    """
    return Linear1D(slope=spectral_width/(1*u.pix), intercept=reference_val)


@u.quantity_input
def linear_time_model(cadence: u.s, reference_val: u.s = None):
    """
    A linear model in a temporal dimension. The reference pixel is always 0.
    """
    if not reference_val:
        reference_val = 0 * cadence.unit
    return Linear1D(slope=cadence/(1*u.pix), intercept=reference_val)


def time_model_from_date_obs(date_obs, date_bgn=None):
    """
    Return a time model that best fits a list of dateobs's.
    """
    if not date_bgn:
        date_bgn = date_obs[0]
    date_obs = Time(date_obs)
    date_bgn = Time(date_bgn)

    deltas = date_bgn - date_obs

    # Work out if we have a uniform delta (i.e. a linear model)
    ddelta = (deltas.to(u.s)[:-1] - deltas.to(u.s)[1:])

    if u.allclose(ddelta[0], ddelta):
        slope = ddelta[0]
        intercept = 0 * u.s
        return linear_time_model(cadence=slope, reference_val=intercept)
    else:
        return LookupTable(deltas)


def make_asdf(filename, *, dataset, gwcs, **kwargs):
    """
    Save an asdf file.

    All keyword arguments become keys in the top level of the asdf tree.
    """
    tree = {
        'gwcs': gwcs,
        'dataset': dataset,
        **kwargs
    }

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(str(filename))

    return filename
