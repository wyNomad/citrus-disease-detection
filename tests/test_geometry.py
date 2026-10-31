import numpy as np
import pytest

from citrus_vision.config import LocalizationConfig
from citrus_vision.geometry import Intrinsics, depth_in_metres, sample_depth, deproject


def test_pixel_ray_has_expected_optical_axes_and_metres():
    camera = Intrinsics(640, 480, 600, 600, 320, 240)
    assert deproject(320, 240, 2, camera) == (0, 0, 2)
    assert deproject(380, 300, 2, camera) == pytest.approx((0.2, 0.2, 2))
    assert deproject(260, 180, 2, camera) == pytest.approx((-0.2, -0.2, 2))


def test_depth_encodings_do_not_double_scale_float_metres():
    assert depth_in_metres(np.array([[1000]], np.uint16), "16UC1", .001)[0, 0] == 1
    assert depth_in_metres(np.array([[1]], np.float32), "32FC1", .001)[0, 0] == 1


@pytest.mark.parametrize("depth,encoding", [
    (np.zeros((2, 2), np.uint8), "16UC1"),
    (np.zeros((2, 2), np.uint16), "32FC1"),
    (np.zeros((2, 2, 3)), "16UC1"),
    (np.zeros((2, 2)), "8UC1"),
])
def test_invalid_depth_encoding_is_rejected(depth, encoding):
    with pytest.raises(ValueError):
        depth_in_metres(depth, encoding, .001)


def test_median_filters_holes_nonfinite_and_out_of_range_values():
    depth = np.array([[0, 1, 3], [np.nan, 2, np.inf], [20, 0, 0]])
    assert sample_depth(depth, 1, 1, LocalizationConfig(sample_radius=1)) == 2


def test_border_uses_true_even_median():
    depth = np.array([[1., 3.], [0., 0.]])
    assert sample_depth(depth, 0, 0, LocalizationConfig(sample_radius=1)) == 2


@pytest.mark.parametrize("u,v", [(-1, 1), (3, 1), (1, 3), (float('nan'), 1)])
def test_pixel_outside_depth_is_invalid(u, v):
    assert sample_depth(np.ones((3, 3)), u, v, LocalizationConfig()) is None


def test_no_valid_depth_returns_none():
    assert sample_depth(np.zeros((3, 3)), 1, 1, LocalizationConfig()) is None


def test_uncalibrated_intrinsics_are_rejected():
    with pytest.raises(ValueError):
        Intrinsics(640, 480, 0, 600, 320, 240)


def test_distorted_pixel_is_corrected_before_deprojection():
    cv2 = pytest.importorskip("cv2")
    camera = Intrinsics(640, 480, 600, 600, 320, 240, (.1, -.05, 0, 0, 0))
    ray = np.array([[[.1, .2, 1.]]], dtype=np.float64)
    matrix = np.array([[600., 0, 320], [0, 600, 240], [0, 0, 1]])
    pixel, _ = cv2.projectPoints(ray, np.zeros(3), np.zeros(3), matrix, np.array(camera.distortion))
    u, v = pixel.reshape(2)
    assert deproject(u, v, 2, camera) == pytest.approx((.2, .4, 2), abs=1e-6)
