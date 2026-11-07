"""LLM Critic reply parsing and its call, offline (a stand-in LLM returns fixed text)."""

from langchain_core.messages import AIMessage

from options_trade_analyzer.agents import critic


def test_parse_reads_json_even_with_text_around_it():
    reply = 'Here is my review:\n{"issues": [{"agent": "writer", "check": 2, "problem": "Earnings after expiry listed as a risk.", "evidence": "next_earnings_date 2027-01-28"}]}\nDone.'
    judgments, error = critic.parse(reply)
    assert error is None
    assert judgments == [critic.Judgment("writer", "Earnings after expiry listed as a risk.", "next_earnings_date 2027-01-28", 2)]
    assert judgments[0].as_issue().startswith("Judgment issue for writer: Earnings after expiry")


def test_parse_sends_unknown_owners_to_the_writer_and_drops_empty_items():
    judgments, _ = critic.parse('{"issues": [{"agent": "ceo", "problem": "x"}, {"agent": "writer", "problem": " "}, "junk"]}')
    assert [j.agent for j in judgments] == ["writer"]


def test_parse_failures_count_as_no_issues_with_a_reason():
    for reply in ("looks fine to me", '{"issues": [', '{"verdict": "ok"}'):
        judgments, error = critic.parse(reply)
        assert judgments == [] and error


def test_parse_caps_the_number_of_issues():
    many = '{"issues": [' + ",".join('{"agent": "writer", "problem": "p%d"}' % i for i in range(9)) + "]}"
    assert len(critic.parse(many)[0]) == critic.MAX_ISSUES


def test_review_sends_the_report_and_the_evidence():
    class FakeLLM:
        def invoke(self, messages):
            self.messages = messages
            return AIMessage(content='{"issues": []}')

    llm = FakeLLM()
    judgments, error, _ = critic.review(llm, "## Evidence\\n[get_earnings_date] {...}", "Summary: ...")
    assert judgments == [] and error is None
    assert "Report to review" in llm.messages[1].content and "Evidence" in llm.messages[1].content
