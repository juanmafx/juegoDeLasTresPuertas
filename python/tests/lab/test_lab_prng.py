import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from monty_hall.lab.prng import MASK64, SplitMix64, Xoshiro256StarStar

seeds = st.integers(0, MASK64)


def test_splitmix64_seed_zero_matches_published_first_output() -> None:
    assert SplitMix64(0).next() == 0xE220A8397B1DCDAF


def test_xoshiro_words_match_independent_c_transcription() -> None:
    rng = Xoshiro256StarStar(0)
    assert [rng.next_u64() for _ in range(5)] == [
        11091344671253066420,
        13793997310169335082,
        1900383378846508768,
        7684712102626143532,
        13521403990117723737,
    ]


def test_bounded_rejection_path_matches_independent_c_transcription() -> None:
    rng = Xoshiro256StarStar(42)
    for _ in range(10):
        rng.next_u64()
    assert [rng.bounded(2**63 + 1) for _ in range(3)] == [
        2681029139591840946,
        7388145106668446555,
        8095973720557042685,
    ]


@pytest.mark.parametrize("bound", [0, 2**64])
def test_bounded_rejects_out_of_range(bound: int) -> None:
    with pytest.raises(ValueError, match="bound"):
        Xoshiro256StarStar(1).bounded(bound)


@pytest.mark.parametrize("weights", [[], [0, 0], [1, -1]])
def test_weighted_index_rejects_invalid_weights(weights: list[int]) -> None:
    with pytest.raises(ValueError, match="weights"):
        Xoshiro256StarStar(1).weighted_index(weights)


def test_seed_must_be_unsigned_64_bit() -> None:
    with pytest.raises(ValueError, match="seed"):
        SplitMix64(-1)


@settings(derandomize=True, max_examples=200)
@given(seeds, st.integers(1, MASK64))
def test_bounded_stays_in_range(seed: int, bound: int) -> None:
    rng = Xoshiro256StarStar(seed)
    assert all(0 <= rng.bounded(bound) < bound for _ in range(5))


@settings(derandomize=True, max_examples=200)
@given(seeds, st.lists(st.integers(0, 50), min_size=1, max_size=12).filter(lambda w: sum(w) > 0))
def test_weighted_index_never_picks_zero_weight(seed: int, weights: list[int]) -> None:
    rng = Xoshiro256StarStar(seed)
    assert all(weights[rng.weighted_index(weights)] > 0 for _ in range(10))


@settings(derandomize=True, max_examples=200)
@given(seeds, st.integers(1, 80))
def test_shuffle_is_a_permutation(seed: int, size: int) -> None:
    items = list(range(size))
    Xoshiro256StarStar(seed).shuffle(items)
    assert sorted(items) == list(range(size))


@settings(derandomize=True, max_examples=100)
@given(seeds, st.integers(1, 30), st.data())
def test_unit_weights_draw_the_same_as_uniform_indices(
    seed: int, size: int, data: st.DataObject
) -> None:
    count = data.draw(st.integers(0, size))
    weighted = Xoshiro256StarStar(seed).weighted_sample(list(range(size)), [1] * size, count)
    rng = Xoshiro256StarStar(seed)
    pool = list(range(size))
    uniform = [pool.pop(rng.bounded(len(pool))) for _ in range(count)]
    assert weighted == uniform
