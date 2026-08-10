from forge_python.system_monitor import collect_stats


def test_collect_stats_has_cpu_ram() -> None:
    stats = collect_stats(queue_pending=2, queue_processing=1)
    assert stats.cpu_percent >= 0
    assert stats.ram_percent >= 0
    assert stats.ram_total_gb > 0
    assert stats.queue_pending == 2
    assert stats.queue_processing == 1
