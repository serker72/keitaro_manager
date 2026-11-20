"""Unit tests for the weight recalculation algorithm (Этап 4)."""

import pytest

from src.schemas.api import StreamOfferRow
from src.services.stream_editor import StreamValidationError, recalculate_weights, validate_shares


def offer(
    offer_id: int,
    name: str | None = None,
    share: int = 0,
    is_pinned: bool = False,
    is_removed: bool = False,
) -> StreamOfferRow:
    return StreamOfferRow(
        offer_id=offer_id,
        offer_name=name or f"Offer {offer_id}",
        share=share,
        is_pinned=is_pinned,
        is_removed=is_removed,
    )


def shares(offers: list[StreamOfferRow]) -> list[int]:
    return [o.share for o in offers]


class TestRecalculateWeights:
    def test_three_equal_offers(self) -> None:
        """3 оффера без pin -> 34/33/33."""
        result = recalculate_weights([offer(1), offer(2), offer(3)])
        assert shares(result) == [34, 33, 33]
        assert sum(shares(result)) == 100

    def test_two_offers(self) -> None:
        result = recalculate_weights([offer(1), offer(2)])
        assert shares(result) == [50, 50]

    def test_single_offer_gets_100(self) -> None:
        result = recalculate_weights([offer(1)])
        assert shares(result) == [100]

    def test_pinned_keeps_share(self) -> None:
        """1 запиненный на 25% + 2 обычных -> 25/38/37 (остаток 75)."""
        result = recalculate_weights([offer(1, share=25, is_pinned=True), offer(2), offer(3)])
        assert shares(result) == [25, 38, 37]
        assert sum(shares(result)) == 100

    def test_pinned_share_preserved_even_if_odd(self) -> None:
        """Запиненный сохраняет своё значение как есть."""
        result = recalculate_weights([offer(1, share=13, is_pinned=True), offer(2), offer(3)])
        assert result[0].share == 13
        assert sum(shares(result)) == 100

    def test_pin_100_percent(self) -> None:
        """Кейс pin=100%: остальные активные получают 0."""
        result = recalculate_weights([offer(1, share=100, is_pinned=True), offer(2), offer(3)])
        assert shares(result) == [100, 0, 0]

    def test_removed_offer_zero_and_excluded(self) -> None:
        """Удалённый оффер: share=0, в делении не участвует."""
        result = recalculate_weights([offer(1), offer(2), offer(3, is_removed=True)])
        assert shares(result) == [50, 50, 0]

    def test_restore_removed_gets_share(self) -> None:
        """BRING BACK: восстановленный участвует в пересчёте."""
        restored = offer(3, is_removed=False)
        result = recalculate_weights([offer(1), offer(2), restored])
        assert shares(result) == [34, 33, 33]

    def test_order_preserved(self) -> None:
        rows = [offer(10), offer(20), offer(30)]
        result = recalculate_weights(rows)
        assert [o.offer_id for o in result] == [10, 20, 30]

    def test_pinned_sum_over_100_unpinned_zero(self) -> None:
        result = recalculate_weights([offer(1, share=60, is_pinned=True), offer(2, share=60, is_pinned=True), offer(3)])
        assert shares(result) == [60, 60, 0]

    def test_no_offers(self) -> None:
        assert recalculate_weights([]) == []

    def test_flags_preserved(self) -> None:
        result = recalculate_weights([offer(1, is_pinned=True, share=40), offer(2), offer(3, is_removed=True)])
        assert result[0].is_pinned is True
        assert result[1].is_pinned is False
        assert result[2].is_removed is True


class TestValidateShares:
    def test_valid_100(self) -> None:
        validate_shares([offer(1, share=50), offer(2, share=50)])

    def test_removed_not_counted(self) -> None:
        validate_shares([offer(1, share=100), offer(2, share=0, is_removed=True)])

    def test_sum_below_100(self) -> None:
        with pytest.raises(StreamValidationError):
            validate_shares([offer(1, share=50)])

    def test_sum_above_100(self) -> None:
        with pytest.raises(StreamValidationError):
            validate_shares([offer(1, share=60), offer(2, share=60)])
