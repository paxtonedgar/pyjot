from .base import Target


class SamplingTarget(Target):
    """A target that forwards only a fraction of traces, chosen by trace id"""

    def __init__(self, target, ratio):
        if not 0.0 <= ratio <= 1.0:
            raise ValueError(f"Sampling ratio must be between 0.0 and 1.0, got {ratio}")
        self.target = target

        # Same rule as OpenTelemetry's TraceIdRatioBased sampler: keep a trace when the low 64
        # bits of its id fall below the threshold. Every span in a trace, in every process that
        # sees the same trace id, gets the same decision.
        self._threshold = round(ratio * 2**64)

    def accepts_log_level(self, level):
        return self.target.accepts_log_level(level)

    def finish(self, tags, span):
        if int.from_bytes(span.trace_id[-8:], "big") < self._threshold:
            self.target.finish(tags, span)

    def event(self, name, tags, span=None):
        self.target.event(name, tags, span)

    def log(self, level, message, tags, span=None):
        self.target.log(level, message, tags, span)

    def error(self, message, exception, tags, span=None):
        self.target.error(message, exception, tags, span)

    def magnitude(self, name, value, tags, span=None):
        self.target.magnitude(name, value, tags, span)

    def count(self, name, value, tags, span=None):
        self.target.count(name, value, tags, span)
