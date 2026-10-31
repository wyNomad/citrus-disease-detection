"""CI must fail when a required dependency causes a test to be skipped."""

import os


def pytest_sessionfinish(session, exitstatus):
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if (os.environ.get("CITRUS_FAIL_ON_SKIP") == "1" and exitstatus == 0
            and reporter is not None and reporter.stats.get("skipped")):
        reporter.write_sep("=", "Required tests were skipped; failing this CI job")
        session.exitstatus = 1
