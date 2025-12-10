from typing import Any, Dict


def generate_copy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate outbound SMS/email copy based on role and context.

    Input context:
      - role: "rei" | "buyers" | "govcon" | "generic"
      - address / market / title / etc. (role-specific)

    Returns:
      - channel: "sms" | "email"
      - variant: template identifier
      - body: message text
      - subject: (email only)
    """
    role = ctx.get("role", "generic")

    if role == "rei":
        return _generate_rei_copy(ctx)
    elif role == "buyers":
        return _generate_buyers_copy(ctx)
    elif role == "govcon":
        return _generate_govcon_copy(ctx)
    else:
        return _generate_generic_copy(ctx)


def _generate_rei_copy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Generate copy for REI seller outreach"""
    address = ctx.get("address", "your property")
    spread = ctx.get("spread")
    arv = ctx.get("arv")

    # Variant selection based on context
    if spread and spread >= 50000:
        # High-value deal - more aggressive
        return {
            "channel": "sms",
            "variant": "rei_high_value_v1",
            "body": (
                f"Hi! I'm interested in {address}. "
                f"I can make a quick cash offer and close in 7-10 days. "
                f"Would you be open to discussing?"
            ),
        }
    else:
        # Standard outreach
        return {
            "channel": "sms",
            "variant": "rei_standard_v1",
            "body": (
                f"Hi, I'm looking at {address}. "
                f"Would you consider a straightforward cash offer with a quick close?"
            ),
        }


def _generate_buyers_copy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Generate copy for buyer outreach"""
    market = ctx.get("market", "your area")
    deal_count = ctx.get("deal_count", 1)
    spread = ctx.get("spread")

    if deal_count > 1:
        # Multiple deals available
        return {
            "channel": "sms",
            "variant": "buyers_multi_v1",
            "body": (
                f"Got {deal_count} fresh off-market deals in {market}. "
                f"Are you actively buying this month?"
            ),
        }
    elif spread and spread >= 40000:
        # High-spread single deal
        return {
            "channel": "sms",
            "variant": "buyers_high_spread_v1",
            "body": (
                f"Just locked in a strong deal in {market} - excellent spread. "
                f"Interested in details?"
            ),
        }
    else:
        # Standard buyer blast
        return {
            "channel": "sms",
            "variant": "buyers_standard_v1",
            "body": (
                f"New off-market opportunity in {market}. "
                f"Want the details?"
            ),
        }


def _generate_govcon_copy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Generate copy for GovCon teaming outreach"""
    title = ctx.get("title", "this opportunity")
    agency = ctx.get("agency", "the agency")
    naics = ctx.get("naics")

    subject = f"Teaming opportunity - {title[:50]}"

    if naics:
        body = (
            f"Quick note - we're tracking the {title} opportunity with {agency}. "
            f"Our team covers NAICS {naics} and we may be a strong fit as a subcontractor. "
            f"Are you open to discussing teaming arrangements for this solicitation?"
        )
    else:
        body = (
            f"We're tracking the {title} opportunity with {agency}. "
            f"Are you pursuing this and open to teaming discussions?"
        )

    return {
        "channel": "email",
        "variant": "govcon_teaming_v1",
        "subject": subject,
        "body": body,
    }


def _generate_generic_copy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Generic fallback copy"""
    return {
        "channel": "sms",
        "variant": "generic_v1",
        "body": "Quick question - are you open to new deals or opportunities this month?",
    }


# Template variants for A/B testing
TEMPLATE_VARIANTS = {
    "rei_high_value_v1": {
        "tags": ["urgent", "cash", "quick_close"],
        "tone": "direct",
    },
    "rei_standard_v1": {
        "tags": ["polite", "cash", "flexible"],
        "tone": "friendly",
    },
    "buyers_multi_v1": {
        "tags": ["volume", "urgent", "exclusive"],
        "tone": "professional",
    },
    "buyers_high_spread_v1": {
        "tags": ["value", "exclusive", "urgent"],
        "tone": "professional",
    },
    "buyers_standard_v1": {
        "tags": ["opportunity", "simple"],
        "tone": "casual",
    },
    "govcon_teaming_v1": {
        "tags": ["professional", "teaming", "formal"],
        "tone": "business",
    },
    "generic_v1": {
        "tags": ["generic", "polite"],
        "tone": "neutral",
    },
}
