# -*- coding: utf-8 -*-

""" Test for dji-firmware-tools, known partition images extraction check.

    This test prepares files for deeper verification by extracting
    single files from partition images.
"""

# Copyright (C) 2023 Mefistotelis <mefistotelis@gmail.com>
# Copyright (C) 2023 Original Gangsters <https://dji-rev.slack.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import filecmp
import glob
import itertools
import logging
import os
import re
import subprocess
import sys
import pathlib
import pytest
from unittest.mock import patch

# Import the functions to be tested
sys.path.insert(0, './')
import filediff
from dji_imah_fwsig import main as dji_imah_fwsig_main


LOGGER = logging.getLogger(__name__)


def case_bin_bootimg_extract(img_inp_fn):
    """ Test case for extraction check, and prepare data for tests which use the extracted files.
    """
    LOGGER.info("Testcase file: {:s}".format(img_inp_fn))

    import mmap

    ignore_unknown_format = False

    # We expect the input file to be in a folder which identifies the module
    inp_path, inp_filename = os.path.split(img_inp_fn)
    img_base_name, img_fileext = os.path.splitext(inp_filename)
    match = re.search(r'^(.*_m?([0-9]{4}))[.-].*$', inp_path, flags=re.IGNORECASE)
    assert match, "File path does not identify module: {:s}".format(img_inp_fn)
    inp_path = match.group(1)
    inp_path, modl_base_name = os.path.split(inp_path)
    inp_module = match.group(2)

    inp_path = pathlib.Path(inp_path)
    if len(inp_path.parts) > 1:
        out_path = os.sep.join(["out"] + list(inp_path.parts[1:]))
    else:
        out_path = "out"

    magic_defs = [
      ("img.sig",  b'IM\x2aH\x01', 0,),
      ("img.sig",  b'IM\x2aH\x02', 0,),
      ("partab",   b'PL\x2aI\x00\x00\x00\x00', 0,),
      ("squashfs", b'sqsh', 0,),
    ]
    with open(img_inp_fn, "r+b") as wfh:
        chunks = []
        mm = mmap.mmap(wfh.fileno(), 0)
        # Find chunks
        for magic_ext, magic_val, magic_pos in magic_defs:
            offs = 0
            while True:
                offs = mm.find(magic_val, offs)
                if offs < 0: break
                # Accept only aligned chunks
                if (offs - magic_pos) & 0xf != 0:
                    offs += len(magic_val)
                    continue
                chunks.append( (offs - magic_pos, magic_ext,) )
                offs += len(magic_val)
        # Make sure whole file is assigned to chunks
        if 0 not in [chunk[0] for chunk in chunks]:
            chunks.append( ( 0, "bin",) )
        chunks.append( ( mm.size(), None,) )
        chunks.sort(key=lambda chunk: chunk[0])
        # Extract the chunks
        for i in range(len(chunks)-1):
            cuchk = chunks[i]
            nxchk = chunks[i+1]
            img_part_ext = cuchk[1]
            ofs_beg = cuchk[0]
            ofs_end = nxchk[0]
            img_chunk_fn = os.sep.join([out_path, "{:s}-{:s}_p{:d}.{:s}".format(modl_base_name, img_base_name, i, img_part_ext)])
            with open(img_chunk_fn, "wb") as cfh:
                cfh.write(mm[ofs_beg:ofs_end])
        pass
    pass


@pytest.mark.order(3) # must be run after test_bin_archives_imah_v1_extract
@pytest.mark.fw_imah_v1
@pytest.mark.parametrize("modl_inp_dir,test_nth", [
    ('out/ag407-agras_mg-1p-rtk',1,),
    ('out/ag408-agras_mg-unk',1,),
    ('out/ag410-agras_t16',1,),
    ('out/ag411-agras_t20',1,),
    ('out/gl811-goggles_racing_ed',1,),
    ('out/pm410-matrice200',1,),
    ('out/pm420-matrice200_v2',1,),
    ('out/rc220-mavic_rc',1,),
    ('out/rc240-mavic_2_rc',1,),
    ('out/tp703-aeroscope',1,),
    ('out/wm100-spark',1,),
    ('out/wm220-goggles_std',1,),
    ('out/wm220-mavic',1,),
    ('out/wm222-mavic_sp',1,),
    ('out/wm330-phantom_4_std',1,),
    ('out/wm331-phantom_4_pro',1,),
    ('out/wm332-phantom_4_adv',1,),
    ('out/wm334-phantom_4_rtk',1,),
    ('out/wm336-phantom_4_mulspectral',1,),
    ('out/wm620-inspire_2',1,),
    ('out/xw607-robomaster_s1',1,),
    ('out/zv811-occusync_air_sys',1,),
  ] )
def test_bin_bootimg_imah_v1_extract(capsys, modl_inp_dir, test_nth):
    """ Test if boot images are extracting correctly, and prepare data for tests which use the extracted files.
    """
    if test_nth < 1:
        pytest.skip("limited scope")

    img_inp_filenames = [fn for fn in itertools.chain.from_iterable([ glob.glob(e, recursive=True) for e in (
        # Some Android OTA/TGZ/TAR modules contain boot images with another stage of IMaH encryption
        "{}/*/*_0801-extr1/bootarea.img".format(modl_inp_dir),
        "{}/*/*_1301-extr1/bootarea.img".format(modl_inp_dir),
        "{}/*/*_2801-extr1/bootarea.img".format(modl_inp_dir),
      ) ]) if os.path.isfile(fn)]

    if len(img_inp_filenames) < 1:
        pytest.skip("no package files to test in this directory")

    for img_inp_fn in img_inp_filenames:
        case_bin_bootimg_extract(img_inp_fn)
        capstdout, _ = capsys.readouterr()
    pass
