"""Closed vocabularies shared by the wire contract, the label schema and the policy engine.

Every enum here is part of the versioned public contract. Adding a member is a minor
version bump; removing or renaming one is a major bump.
See ``docs/adr/0002-contract-versioning.md``.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AbstentionReason",
    "AuthMethod",
    "CalibrationMethod",
    "Decision",
    "DecisionMode",
    "DestinationRelationship",
    "ErrorCode",
    "FeedbackOutcome",
    "LabelValue",
    "ObligationKind",
    "OperationKind",
    "PrincipalType",
    "ResourceKind",
    "RiskDimension",
    "RuleKind",
    "Sensitivity",
    "Stage",
    "ToolFamily",
    "TrustLevel",
]


class RiskDimension(StrEnum):
    """The atomic facts the learned model scores.

    These are deliberately *descriptive*, not *normative*. ``financial_commitment`` is
    true of a legitimate authorised payment as well as a fraudulent one; whether that
    is acceptable is the policy engine's decision, never the model's.
    """

    PROMPT_INJECTION_INFLUENCE = "prompt_injection_influence"
    """The proposed action is materially influenced by untrusted content rather than by
    the authenticated principal's stated objective."""

    UNAUTHORIZED_SCOPE = "unauthorized_scope"
    """The action falls outside the delegated permissions or the principal's roles."""

    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    """The action moves data whose sensitivity exceeds the sensitivity of the sink."""

    UNTRUSTED_DESTINATION = "untrusted_destination"
    """The destination is external, unknown, or a look-alike of a known destination."""

    PRIVILEGE_ESCALATION = "privilege_escalation"
    """The action grants, widens, or acquires authority beyond the current grant."""

    DESTRUCTIVE_OR_IRREVERSIBLE_ACTION = "destructive_or_irreversible_action"
    """The action destroys state or cannot be undone by an equivalent inverse action."""

    FINANCIAL_COMMITMENT = "financial_commitment"
    """The action creates a monetary obligation or moves funds."""

    EXTERNAL_COMMUNICATION = "external_communication"
    """The action emits a message to a party outside the trust boundary."""

    POLICY_CONFLICT = "policy_conflict"
    """The action contradicts at least one supplied organizational policy statement."""

    SUSPICIOUS_ACTION_SEQUENCE = "suspicious_action_sequence"
    """The trajectory as a whole forms a recognisable attack shape even where each step
    is individually unremarkable."""

    INSUFFICIENT_CONTEXT = "insufficient_context"
    """The supplied context does not determine the other dimensions. This is a
    first-class output, not an error: it is how the model abstains."""


# Not derivable from the latent scenario alone, so must never drive an automatic DENY.
META_DIMENSIONS: frozenset[RiskDimension] = frozenset({RiskDimension.INSUFFICIENT_CONTEXT})


class LabelValue(StrEnum):
    """Ground-truth value for one dimension of one example.

    ``NOT_APPLICABLE`` is distinct from ``NO``: a read-only query has no destination, so
    ``untrusted_destination`` is not applicable rather than false. Metrics exclude
    ``NOT_APPLICABLE`` cells rather than counting them as negatives, which otherwise
    inflates precision on rare positives.
    """

    YES = "yes"
    NO = "no"
    NOT_APPLICABLE = "not_applicable"
    UNDETERMINED = "undetermined"


class Decision(StrEnum):
    """Output of the deterministic policy engine."""

    ALLOW = "allow"
    REVIEW = "review"
    DENY = "deny"


class DecisionMode(StrEnum):
    """How a policy bundle turns scores into a decision.

    ``THRESHOLD`` (the default) is today's per-rule most-restrictive-wins
    combination. ``EXPECTED_COST`` picks the decision that minimises expected cost
    over the bundle's covered dimensions, using the calibrated probability vector
    jointly instead of independent per-rule thresholds. See
    ``docs/policy-dsl.md``.
    """

    THRESHOLD = "threshold"
    EXPECTED_COST = "expected_cost"


class TrustLevel(StrEnum):
    """Provenance of a piece of context, ordered from most to least trusted.

    The distinction that matters most is ``PRINCIPAL`` (the human said it) versus
    ``UNTRUSTED`` (a web page, an email body, or a tool result said it). Instructions
    found in ``UNTRUSTED`` content are data, never commands.
    """

    PRINCIPAL = "principal"
    SYSTEM = "system"
    TRUSTED_TOOL = "trusted_tool"
    UNTRUSTED = "untrusted"
    UNKNOWN = "unknown"


class PrincipalType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"
    AGENT = "agent"
    ANONYMOUS = "anonymous"


class AuthMethod(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SSO = "sso"
    MTLS = "mtls"
    SESSION = "session"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    """Data classification of an affected resource. Ordered."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"  # noqa: S105


SENSITIVITY_ORDER: dict[Sensitivity, int] = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
    Sensitivity.SECRET: 4,
}


class OperationKind(StrEnum):
    READ = "read"
    LIST = "list"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    GRANT = "grant"
    REVOKE = "revoke"
    TRANSFER = "transfer"


MUTATING_OPERATIONS: frozenset[OperationKind] = frozenset(
    {
        OperationKind.CREATE,
        OperationKind.UPDATE,
        OperationKind.DELETE,
        OperationKind.EXECUTE,
        OperationKind.GRANT,
        OperationKind.REVOKE,
        OperationKind.TRANSFER,
    }
)


class ResourceKind(StrEnum):
    FILE = "file"
    OBJECT_STORE = "object_store"
    DATABASE = "database"
    TABLE = "table"
    SECRET = "secret"  # noqa: S105
    CREDENTIAL = "credential"
    REPOSITORY = "repository"
    PIPELINE = "pipeline"
    COMPUTE = "compute"
    NETWORK = "network"
    IAM_PRINCIPAL = "iam_principal"
    IAM_POLICY = "iam_policy"
    MAILBOX = "mailbox"
    CHANNEL = "channel"
    CRM_RECORD = "crm_record"
    TICKET = "ticket"
    PAYMENT_METHOD = "payment_method"
    INVOICE = "invoice"
    EMPLOYEE_RECORD = "employee_record"
    BROWSER_PAGE = "browser_page"
    MODEL_ENDPOINT = "model_endpoint"
    OTHER = "other"


class RuleKind(StrEnum):
    """How a fired policy rule participates in most-restrictive-wins combination.

    ``ALLOW_OVERRIDE`` is a deliberate escape hatch: it may force ``ALLOW`` even when a
    non-hard restrictive rule also fired, but it can never override a rule flagged
    ``hard: true``.
    """

    STANDARD = "standard"
    ALLOW_OVERRIDE = "allow_override"


class DestinationRelationship(StrEnum):
    """How the destination relates to the principal's trust boundary."""

    SELF = "self"
    SAME_TENANT = "same_tenant"
    KNOWN_THIRD_PARTY = "known_third_party"
    UNKNOWN_EXTERNAL = "unknown_external"
    LOOKALIKE = "lookalike"
    """Resembles a known destination but is not it, e.g. a homoglyph domain."""


class Stage(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ToolFamily(StrEnum):
    """Coarse tool taxonomy. Drives domain slicing in evaluation and
    held-out-family splitting in the data pipeline."""

    EMAIL_MESSAGING = "email_messaging"
    CLOUD_ADMIN = "cloud_admin"
    SHELL_CODE_EXEC = "shell_code_exec"
    SOURCE_CONTROL_CICD = "source_control_cicd"
    DATABASE_WAREHOUSE = "database_warehouse"
    FILE_STORAGE = "file_storage"
    CRM_SUPPORT = "crm_support"
    PAYMENTS_PROCUREMENT = "payments_procurement"
    HR_IDENTITY = "hr_identity"
    BROWSER = "browser"
    MCP = "mcp"
    PRODUCTION_OPS = "production_ops"


class CalibrationMethod(StrEnum):
    NONE = "none"
    TEMPERATURE = "temperature"
    VECTOR = "vector"
    ISOTONIC = "isotonic"
    BETA = "beta"


class AbstentionReason(StrEnum):
    CONTEXT_TRUNCATED = "context_truncated"
    LOW_CONFIDENCE = "low_confidence"
    UNCALIBRATED_MODEL = "uncalibrated_model"
    MISSING_REQUIRED_CONTEXT = "missing_required_context"
    BACKEND_TIMEOUT = "backend_timeout"
    ITEM_FAILED = "item_failed"
    """A batch item raised an unexpected error; isolated from its batch-mates."""


class FeedbackOutcome(StrEnum):
    """The human's real-world outcome on a forecheck decision, mostly a REVIEW.

    This is the label flywheel: every outcome is a data point for refitting
    calibration and policy thresholds on real traffic rather than synthetic data.
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ObligationKind(StrEnum):
    """Side conditions a policy rule can attach to a decision."""

    REQUIRE_HUMAN_APPROVAL = "require_human_approval"
    REQUIRE_STEP_UP_AUTH = "require_step_up_auth"
    REDACT_ARGUMENTS = "redact_arguments"
    LOG_TO_AUDIT_SINK = "log_to_audit_sink"
    NOTIFY_RESOURCE_OWNER = "notify_resource_owner"
    RATE_LIMIT = "rate_limit"
    DRY_RUN_FIRST = "dry_run_first"


class ErrorCode(StrEnum):
    """Stable machine-readable error codes. Clients switch on these, not on HTTP status."""

    VALIDATION_FAILED = "validation_failed"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    REQUEST_TOO_LARGE = "request_too_large"
    TOO_MANY_TRAJECTORY_STEPS = "too_many_trajectory_steps"
    CONTEXT_TOO_LONG = "context_too_long"
    MODEL_NOT_READY = "model_not_ready"
    BACKEND_TIMEOUT = "backend_timeout"
    BACKEND_ERROR = "backend_error"
    POLICY_BUNDLE_NOT_FOUND = "policy_bundle_not_found"
    POLICY_BUNDLE_INVALID = "policy_bundle_invalid"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
