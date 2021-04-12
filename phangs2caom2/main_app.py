# -*- coding: utf-8 -*-
# ***********************************************************************
# ******************  CANADIAN ASTRONOMY DATA CENTRE  *******************
# *************  CENTRE CANADIEN DE DONNÉES ASTRONOMIQUES  **************
#
#  (c) 2020.                            (c) 2020.
#  Government of Canada                 Gouvernement du Canada
#  National Research Council            Conseil national de recherches
#  Ottawa, Canada, K1A 0R6              Ottawa, Canada, K1A 0R6
#  All rights reserved                  Tous droits réservés
#
#  NRC disclaims any warranties,        Le CNRC dénie toute garantie
#  expressed, implied, or               énoncée, implicite ou légale,
#  statutory, of any kind with          de quelque nature que ce
#  respect to the software,             soit, concernant le logiciel,
#  including without limitation         y compris sans restriction
#  any warranty of merchantability      toute garantie de valeur
#  or fitness for a particular          marchande ou de pertinence
#  purpose. NRC shall not be            pour un usage particulier.
#  liable in any event for any          Le CNRC ne pourra en aucun cas
#  damages, whether direct or           être tenu responsable de tout
#  indirect, special or general,        dommage, direct ou indirect,
#  consequential or incidental,         particulier ou général,
#  arising from the use of the          accessoire ou fortuit, résultant
#  software.  Neither the name          de l'utilisation du logiciel. Ni
#  of the National Research             le nom du Conseil National de
#  Council of Canada nor the            Recherches du Canada ni les noms
#  names of its contributors may        de ses  participants ne peuvent
#  be used to endorse or promote        être utilisés pour approuver ou
#  products derived from this           promouvoir les produits dérivés
#  software without specific prior      de ce logiciel sans autorisation
#  written permission.                  préalable et particulière
#                                       par écrit.
#
#  This file is part of the             Ce fichier fait partie du projet
#  OpenCADC project.                    OpenCADC.
#
#  OpenCADC is free software:           OpenCADC est un logiciel libre ;
#  you can redistribute it and/or       vous pouvez le redistribuer ou le
#  modify it under the terms of         modifier suivant les termes de
#  the GNU Affero General Public        la “GNU Affero General Public
#  License as published by the          License” telle que publiée
#  Free Software Foundation,            par la Free Software Foundation
#  either version 3 of the              : soit la version 3 de cette
#  License, or (at your option)         licence, soit (à votre gré)
#  any later version.                   toute version ultérieure.
#
#  OpenCADC is distributed in the       OpenCADC est distribué
#  hope that it will be useful,         dans l’espoir qu’il vous
#  but WITHOUT ANY WARRANTY;            sera utile, mais SANS AUCUNE
#  without even the implied             GARANTIE : sans même la garantie
#  warranty of MERCHANTABILITY          implicite de COMMERCIALISABILITÉ
#  or FITNESS FOR A PARTICULAR          ni d’ADÉQUATION À UN OBJECTIF
#  PURPOSE.  See the GNU Affero         PARTICULIER. Consultez la Licence
#  General Public License for           Générale Publique GNU Affero
#  more details.                        pour plus de détails.
#
#  You should have received             Vous devriez avoir reçu une
#  a copy of the GNU Affero             copie de la Licence Générale
#  General Public License along         Publique GNU Affero avec
#  with OpenCADC.  If not, see          OpenCADC ; si ce n’est
#  <http://www.gnu.org/licenses/>.      pas le cas, consultez :
#                                       <http://www.gnu.org/licenses/>.
#
#  $Revision: 4 $
#
# ***********************************************************************
#

"""
This module implements the ObsBlueprint mapping, as well as the workflow 
entry point that executes the workflow.
"""

import importlib
import logging
import os
import sys
import traceback

from math import sqrt

from caom2 import Observation, DataProductType, CalibrationLevel
from caom2utils import ObsBlueprint, get_gen_proc_arg_parser, gen_proc
from caom2pipe import manage_composable as mc


__all__ = ['phangs_main_app', 'update', 'PHANGSName', 'COLLECTION',
           'APPLICATION', 'ARCHIVE', 'to_caom2']


APPLICATION = 'phangs2caom2'
COLLECTION = 'PHANGS'
ARCHIVE = 'PHANGS'


class PHANGSName(mc.StorageName):
    """Naming rules:
    - support mixed-case file name storage, and mixed-case obs id values
    - support uncompressed files in storage
    """

    PHANGS_NAME_PATTERN = '*'

    def __init__(self, obs_id=None, file_name=None, entry=None,
                 artifact_uri=None):
        if file_name:
            self.fname_in_ad = file_name
            super(PHANGSName, self).__init__(
                obs_id, COLLECTION, PHANGSName.PHANGS_NAME_PATTERN,
                fname_on_disk=file_name, compression='', entry=entry)
        elif artifact_uri:
            scheme, path, file_name = mc.decompose_uri(artifact_uri)
        super(PHANGSName, self).__init__(
            obs_id, COLLECTION, PHANGSName.PHANGS_NAME_PATTERN,
            fname_on_disk=file_name, compression='', entry=entry)
        self._file_id = mc.StorageName.remove_extensions(file_name)
        self._obs_id = self.file_id

    @property
    def file_id(self):
        return self._file_id

    @property
    def product_id(self):
        result = 'spectral_line_data_cube'
        if 'derived' in self.file_name:
            result = 'image_intensity_map'
        return result

    def is_valid(self):
        return True


def accumulate_bp(bp, uri):
    """Configure the telescope-specific ObsBlueprint at the CAOM model 
    Observation level."""
    logging.debug('Begin accumulate_bp.')
    bp.configure_position_axes((1, 2))
    bp.configure_energy_axis(3)

    bp.clear('Observation.telescope.name')
    bp.add_fits_attribute('Observation.telescope.name', 'TELESCOP')
    bp.set('Observation.telescope.geoLocationX', 2225015.30883296)
    bp.set('Observation.telescope.geoLocationY', -5440016.41799762)
    bp.set('Observation.telescope.geoLocationZ', -2481631.27428014)

    data_product_type = DataProductType.CUBE
    calibration_level = CalibrationLevel.PRODUCT
    if 'derived' in uri:
        # I'm sure this is wrong
        data_product_type = DataProductType.MEASUREMENTS
        calibration_level = CalibrationLevel.ANALYSIS_PRODUCT

    bp.set('Plane.calibrationLevel', calibration_level)
    bp.set('Plane.dataProductType', data_product_type)
    bp.clear('Plane.dataRelease')
    bp.add_fits_attribute('Plane.dataRelease', 'DATE')
    bp.clear('Plane.metaRelease')
    bp.add_fits_attribute('Plane.metaRelease', 'DATE')

    bp.clear('Plane.provenance.name')
    bp.add_fits_attribute('Plane.provenance.name', 'ORIGIN')
    bp.clear('Plane.provenance.lastExecuted')
    bp.add_fits_attribute('Plane.provenance.lastExecuted', 'DATE')
    bp.clear('Plane.provenance.producer')

    # chunk level
    bp.clear('Chunk.position.axis.function.cd11')
    bp.clear('Chunk.position.axis.function.cd22')
    bp.add_fits_attribute('Chunk.position.axis.function.cd11', 'CDELT1')
    bp.set('Chunk.position.axis.function.cd12', 0.0)
    bp.set('Chunk.position.axis.function.cd21', 0.0)
    bp.add_fits_attribute('Chunk.position.axis.function.cd22', 'CDELT2')
    bp.set('Chunk.position.resolution', '_get_position_resolution(header)')

    logging.debug('Done accumulate_bp.')


def update(observation, **kwargs):
    """Called to fill multiple CAOM model elements and/or attributes (an n:n
    relationship between TDM attributes and CAOM attributes). Must have this
    signature for import_module loading and execution.

    :param observation A CAOM Observation model instance.
    :param **kwargs Everything else."""
    logging.debug('Begin update.')
    mc.check_param(observation, Observation)

    headers = kwargs.get('headers')
    fqn = kwargs.get('fqn')
    uri = kwargs.get('uri')
    phangs_name = None
    if uri is not None:
        phangs_name = PHANGSName(artifact_uri=uri)
    if fqn is not None:
        phangs_name = PHANGSName(file_name=os.path.basename(fqn))
    if phangs_name is None:
        raise mc.CadcException(f'Need one of fqn or uri defined for '
                               f'{observation.observation_id}')

    logging.debug('Done update.')
    return observation


def _build_blueprints(uris):
    """This application relies on the caom2utils fits2caom2 ObsBlueprint
    definition for mapping FITS file values to CAOM model element
    attributes. This method builds the DRAO-ST blueprint for a single
    artifact.

    The blueprint handles the mapping of values with cardinality of 1:1
    between the blueprint entries and the model attributes.

    :param uris The artifact URIs for the files to be processed."""
    module = importlib.import_module(__name__)
    blueprints = {}
    for uri in uris:
        blueprint = ObsBlueprint(module=module)
        if not mc.StorageName.is_preview(uri):
            accumulate_bp(blueprint, uri)
        blueprints[uri] = blueprint
    return blueprints


def _get_position_resolution(header):
    bmaj = header.get('BMAJ')
    bmin = header.get('BMIN')
    # From
    # https://open-confluence.nrao.edu/pages/viewpage.action?pageId=13697486
    # Clare Chandler via JJK - 21-08-18
    return 3600.0 * sqrt(bmaj*bmin)


def _get_uris(args):
    result = []
    if args.local:
        for ii in args.local:
            file_id = mc.StorageName.remove_extensions(os.path.basename(ii))
            file_name = f'{file_id}.fits'
            result.append(PHANGSName(file_name=file_name).file_uri)
    elif args.lineage:
        for ii in args.lineage:
            result.append(ii.split('/', 1)[1])
    else:
        raise mc.CadcException(
            f'Could not define uri from these args {args}')
    return result


def to_caom2():
    """This function is called by pipeline execution. It must have this name.
    """
    args = get_gen_proc_arg_parser().parse_args()
    uris = _get_uris(args)
    blueprints = _build_blueprints(uris)
    result = gen_proc(args, blueprints)
    logging.debug(f'Done {APPLICATION} processing.')
    return result
           

def phangs_main_app():
    args = get_gen_proc_arg_parser().parse_args()
    try:
        result = to_caom2()
        sys.exit(result)
    except Exception as e:
        logging.error(f'Failed {APPLICATION} execution for {args}.')
        tb = traceback.format_exc()
        logging.debug(tb)
        sys.exit(-1)
