#!/usr/bin/env bash

python -m ensurepip
python -m pip install --upgrade pip

python -m pip download pyproj --only-binary :all: --platform macosx_14_0_arm64 --python-version 3.11 --no-deps -d /tmp/pyproj_wheel

mv /tmp/pyproj_wheel/pyproj-3.7.2-cp311-cp311-macosx_14_0_arm64.whl /tmp/pyproj_wheel/pyproj-3.7.2-cp311-cp311-macosx_11_0_arm64.whl
python -m pip install /tmp/pyproj_wheel/pyproj-3.7.2-cp311-cp311-macosx_11_0_arm64.whl --force-reinstall --no-deps
 
python -m pip install /tmp/pyproj_wheel/pyproj-macosx_11_0_arm64.whl --force-reinstall --no-deps
python -m pip install certifi
python -c "from pyproj import Proj; print('pyproj OK')"
 
rm -rf /tmp/pyproj_wheel
 