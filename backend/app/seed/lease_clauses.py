"""Clause variant library for generated demo leases.

Each variant carries the ground-truth label (clause_type + expected severity)
used by the eval suite. `anchor` is a distinctive substring used to locate the
clause's page/bbox after PDF generation.
"""

from dataclasses import dataclass

from app.agents.contracts import ClauseType, Severity


@dataclass(frozen=True)
class ClauseVariant:
    key: str
    heading: str
    text: str
    clause_type: ClauseType | None  # None = boilerplate, not a finding
    severity: Severity | None
    anchor: str


V = ClauseVariant

CLAUSES: dict[str, ClauseVariant] = {
    c.key: c
    for c in [
        # --- Boilerplate (not findings) ---------------------------------
        V(
            "parties",
            "1. Parties and Premises",
            "This Residential Lease Agreement is entered into between the Landlord and the Tenant(s) "
            'named below for the residential premises described herein (the "Premises"), located in '
            "Santa Clara County, California. Tenant shall use the Premises solely as a private residence.",
            None,
            None,
            "solely as a private residence",
        ),
        V(
            "term",
            "2. Term of Tenancy",
            "The initial term of this lease shall be twelve (12) months, commencing on the move-in date "
            "specified on the signature page. If Tenant remains in possession after the initial term with "
            "Landlord's consent, the tenancy shall continue month-to-month unless otherwise agreed.",
            None,
            None,
            "continue month-to-month unless otherwise agreed",
        ),
        # --- Security deposit -------------------------------------------
        V(
            "deposit_ok",
            "3. Security Deposit",
            "Tenant shall pay a security deposit equal to one (1) month's rent. Within 21 days after "
            "Tenant vacates, Landlord shall furnish an itemized statement and refund the balance of the "
            "deposit as required by California Civil Code Section 1950.5.",
            "security_deposit",
            "info",
            "itemized statement and refund the balance",
        ),
        V(
            "deposit_high",
            "3. Security Deposit",
            "Tenant shall pay a security deposit equal to two (2) months' rent prior to occupancy. "
            "The deposit, or any portion thereof, shall be returned within 60 days of move-out at "
            "Landlord's discretion after inspection for damages, cleaning, and any other charges.",
            "security_deposit",
            "high",
            "two (2) months' rent prior to occupancy",
        ),
        # --- Non-refundable fees -----------------------------------------
        V(
            "fees_nonrefundable",
            "4. Move-In Fees",
            "In addition to the security deposit, Tenant shall pay a non-refundable move-in fee of $500 "
            "and a non-refundable redecorating fee of $350. These fees are earned upon receipt and shall "
            "not be applied toward rent or damages under any circumstances.",
            "nonrefundable_fees",
            "high",
            "non-refundable move-in fee of $500",
        ),
        V(
            "fees_admin_ok",
            "4. Administrative Fee",
            "Tenant shall pay a one-time application and administrative fee of $150 covering screening "
            "and account setup costs actually incurred by Landlord.",
            "nonrefundable_fees",
            "info",
            "administrative fee of $150",
        ),
        # --- Early termination -------------------------------------------
        V(
            "early_term_fee",
            "5. Early Termination",
            "If Tenant terminates this lease prior to the expiration of the term for any reason, Tenant "
            "shall pay an early termination fee equal to two (2) months' rent, in addition to rent due "
            "through the date a replacement tenant takes possession.",
            "early_termination",
            "high",
            "early termination fee equal to two (2) months",
        ),
        V(
            "early_term_mitigation",
            "5. Early Termination",
            "If Tenant must vacate before the end of the term, Tenant shall give 30 days' written notice. "
            "Landlord shall make reasonable efforts to re-rent the Premises, and Tenant shall remain "
            "responsible for rent only until a replacement tenancy begins, plus reasonable advertising costs.",
            "early_termination",
            "info",
            "reasonable efforts to re-rent the Premises",
        ),
        # --- Auto-renewal -------------------------------------------------
        V(
            "auto_renew",
            "6. Renewal",
            "This lease shall automatically renew for successive twelve (12) month terms unless either "
            "party delivers written notice of non-renewal at least sixty (60) days before the end of the "
            "then-current term. Tenant's failure to give timely notice binds Tenant to the renewal term.",
            "auto_renewal",
            "caution",
            "automatically renew for successive twelve",
        ),
        # --- Rent increases -----------------------------------------------
        V(
            "rent_increase_cap_breaker",
            "7. Rent Adjustments",
            "Upon any renewal or extension, Landlord may increase the monthly rent by up to fifteen "
            "percent (15%) per year upon thirty (30) days' notice to Tenant.",
            "rent_increase",
            "high",
            "fifteen percent (15%) per year",
        ),
        V(
            "rent_increase_ok",
            "7. Rent Adjustments",
            "Rent shall remain fixed for the initial term. Any increase upon renewal shall comply with "
            "applicable law, including the California Tenant Protection Act where applicable, with written "
            "notice as required by Civil Code Section 827.",
            "rent_increase",
            "info",
            "comply with applicable law",
        ),
        # --- Late fees ----------------------------------------------------
        V(
            "late_fee_high",
            "8. Late Charges",
            "Rent is due on the first of each month with no grace period. If rent is not received by "
            "5:00 PM on the first, Tenant shall pay a late charge of $150 plus $15 per day until paid in "
            "full. Tenant agrees these amounts are reasonable.",
            "late_fees",
            "high",
            "late charge of $150 plus $15 per day",
        ),
        V(
            "late_fee_ok",
            "8. Late Charges",
            "If rent is not received within five (5) calendar days after the due date, Tenant shall pay a "
            "one-time late charge of $50, which the parties agree is a reasonable estimate of Landlord's "
            "administrative costs arising from late payment.",
            "late_fees",
            "info",
            "one-time late charge of $50",
        ),
        # --- Maintenance responsibility -----------------------------------
        V(
            "maintenance_shift",
            "9. Maintenance and Repairs",
            "Tenant accepts full responsibility for all repairs and maintenance of the Premises, "
            "including plumbing, electrical, appliances, and HVAC systems, regardless of cause. Tenant "
            "waives any right to repair and deduct under Civil Code Section 1942.",
            "maintenance_responsibility",
            "high",
            "full responsibility for all repairs",
        ),
        V(
            "maintenance_ok",
            "9. Maintenance and Repairs",
            "Landlord shall maintain the Premises in habitable condition as required by law. Tenant shall "
            "promptly report needed repairs and is responsible for damage caused by Tenant's negligence or "
            "misuse beyond ordinary wear and tear.",
            "maintenance_responsibility",
            "info",
            "maintain the Premises in habitable condition",
        ),
        # --- Landlord entry -----------------------------------------------
        V(
            "entry_no_notice",
            "10. Landlord's Right of Entry",
            "Landlord or Landlord's agents may enter the Premises at any reasonable time without prior "
            "notice for inspection, maintenance, or to show the unit to prospective tenants or buyers.",
            "landlord_entry",
            "high",
            "enter the Premises at any reasonable time without prior notice",
        ),
        V(
            "entry_ok",
            "10. Landlord's Right of Entry",
            "Except in emergencies, Landlord shall give Tenant at least 24 hours' written notice before "
            "entering the Premises, and entry shall occur during normal business hours, as provided by "
            "California Civil Code Section 1954.",
            "landlord_entry",
            "info",
            "at least 24 hours' written notice",
        ),
        # --- Subletting ----------------------------------------------------
        V(
            "sublet_ban",
            "11. Assignment and Subletting",
            "Tenant shall not assign this lease, sublet any portion of the Premises, or host paying "
            "guests, including short-term rental platforms, without Landlord's prior written consent, "
            "which Landlord may withhold in its sole and absolute discretion.",
            "subletting",
            "caution",
            "sole and absolute discretion",
        ),
        # --- Guest limits ---------------------------------------------------
        V(
            "guest_limits",
            "12. Occupancy and Guests",
            "No guest may remain on the Premises for more than seven (7) days in any six-month period "
            "without Landlord's prior written approval. Any guest staying longer shall be deemed an "
            "unauthorized occupant and a material breach of this lease.",
            "guest_limits",
            "caution",
            "more than seven (7) days in any six-month period",
        ),
        # --- Pets -----------------------------------------------------------
        V(
            "pets_fee",
            "13. Pets",
            "One approved pet under 40 pounds is permitted with a pet deposit of $500 and monthly pet "
            "rent of $75. The pet deposit is non-refundable and shall be retained by Landlord upon "
            "move-out regardless of the condition of the Premises.",
            "pets",
            "caution",
            "pet deposit is non-refundable",
        ),
        V(
            "pets_ok",
            "13. Pets",
            "One approved pet is permitted with monthly pet rent of $50. Any pet deposit shall be treated "
            "as part of the refundable security deposit under Civil Code Section 1950.5.",
            "pets",
            "info",
            "treated as part of the refundable security deposit",
        ),
        # --- Utilities -------------------------------------------------------
        V(
            "utilities_rubs",
            "14. Utilities",
            "Tenant shall pay a monthly flat utility charge of $110 under a ratio utility billing system "
            "(RUBS) covering water, sewer, and trash, which Landlord may adjust upon 30 days' notice. "
            "All other utilities shall be placed in Tenant's name.",
            "utilities",
            "caution",
            "ratio utility billing system",
        ),
        # --- Parking ---------------------------------------------------------
        V(
            "parking_fee",
            "15. Parking",
            "One assigned parking space is available for an additional $100 per month. Vehicles parked in "
            "unauthorized areas may be towed at the vehicle owner's expense without further notice.",
            "parking",
            "info",
            "assigned parking space is available",
        ),
        # --- Renter's insurance ----------------------------------------------
        V(
            "insurance_req",
            "16. Renter's Insurance",
            "Tenant shall maintain renter's insurance with liability coverage of at least $100,000 "
            "throughout the tenancy and shall name Landlord as an interested party on the policy.",
            "renters_insurance",
            "info",
            "liability coverage of at least $100,000",
        ),
        # --- Joint & several --------------------------------------------------
        V(
            "joint_several",
            "17. Joint and Several Liability",
            "Each Tenant signing this lease is jointly and severally liable for the full amount of rent "
            "and all obligations under this lease, not merely a proportionate share.",
            "joint_several_liability",
            "caution",
            "jointly and severally liable for the full amount",
        ),
        # --- Liability waiver -------------------------------------------------
        V(
            "liability_waiver",
            "18. Waiver of Liability and Indemnification",
            "Tenant releases Landlord from any and all liability for injury, loss, or damage to persons "
            "or property arising from any cause whatsoever, including Landlord's own negligence, and "
            "agrees to indemnify and hold Landlord harmless from all claims.",
            "liability_waiver",
            "high",
            "including Landlord's own negligence",
        ),
        # --- Attorney's fees ---------------------------------------------------
        V(
            "attorneys_fees_onesided",
            "19. Attorney's Fees",
            "In any action arising out of this lease, Landlord shall be entitled to recover its "
            "attorney's fees and costs from Tenant without limitation. Tenant shall bear Tenant's own "
            "fees and costs in all events.",
            "attorneys_fees",
            "caution",
            "without limitation",
        ),
        # --- Arbitration / jury waiver -----------------------------------------
        V(
            "arbitration_jury_waiver",
            "20. Dispute Resolution",
            "Tenant and Landlord agree that any dispute shall be resolved exclusively by binding "
            "arbitration, and each party knowingly and voluntarily waives the right to a trial by jury "
            "for any claim arising from this lease or the Premises.",
            "arbitration",
            "high",
            "waives the right to a trial by jury",
        ),
        # --- Mold / pest disclosure --------------------------------------------
        V(
            "mold_disclosure",
            "21. Mold and Pest Disclosure",
            "Landlord discloses that the Premises has no known mold conditions affecting habitability. "
            "A pest control service contract covers the building; the most recent treatment notice is "
            "attached as Exhibit B.",
            "mold_pest_disclosure",
            "info",
            "no known mold conditions",
        ),
        # --- Move-out charges ---------------------------------------------------
        V(
            "moveout_cleaning",
            "22. Move-Out",
            "Upon vacating, Tenant shall pay a mandatory professional cleaning fee of $400 and a carpet "
            "shampooing fee of $250, which shall be deducted from the security deposit regardless of the "
            "condition in which the Premises are returned.",
            "moveout_charges",
            "high",
            "mandatory professional cleaning fee of $400",
        ),
        V(
            "moveout_ok",
            "22. Move-Out",
            "Upon vacating, Tenant shall return the Premises in the same condition as received, ordinary "
            "wear and tear excepted. Deductions from the deposit, if any, shall reflect actual costs with "
            "receipts provided in the itemized statement.",
            "moveout_charges",
            "info",
            "actual costs with receipts",
        ),
        # --- As-is ------------------------------------------------------------
        V(
            "as_is",
            "23. Condition of Premises",
            'Tenant accepts the Premises strictly "AS-IS", with all faults, whether apparent or latent, '
            "and waives any claim based on the condition of the Premises, including any implied warranty "
            "of habitability, to the maximum extent permitted.",
            "as_is",
            "high",
            "waives any claim based on the condition",
        ),
    ]
}

# --- Lease compositions ------------------------------------------------------


@dataclass(frozen=True)
class LeaseSpec:
    title: str
    building_key: str
    rent: int
    clauses: list[str]


def _spec(d: dict[str, object]) -> LeaseSpec:
    return LeaseSpec(
        title=str(d["title"]),
        building_key=str(d["building_key"]),
        rent=int(d["rent"]),  # type: ignore[call-overload]
        clauses=list(d["clauses"]),  # type: ignore[call-overload]
    )


_RAW_SPECS: dict[str, dict[str, object]] = {
    "lease_1_cedar_grove_clean": {
        "title": "Residential Lease — Cedar Grove Apartments, Unit B214",
        "building_key": "cedar-grove",
        "rent": 3150,
        "clauses": [
            "parties",
            "term",
            "deposit_ok",
            "fees_admin_ok",
            "early_term_mitigation",
            "rent_increase_ok",
            "late_fee_ok",
            "maintenance_ok",
            "entry_ok",
            "pets_ok",
            "parking_fee",
            "insurance_req",
            "mold_disclosure",
            "moveout_ok",
        ],
    },
    "lease_2_mission_pointe_standard": {
        "title": "Residential Lease — Mission Pointe Villas, Unit 310",
        "building_key": "mission-pointe",
        "rent": 2980,
        "clauses": [
            "parties",
            "term",
            "deposit_ok",
            "auto_renew",
            "late_fee_ok",
            "maintenance_ok",
            "entry_ok",
            "sublet_ban",
            "pets_ok",
            "utilities_rubs",
            "parking_fee",
            "insurance_req",
            "joint_several",
            "moveout_ok",
        ],
    },
    "lease_3_marlow_commons_fees": {
        "title": "Residential Lease — Marlow Commons, Unit C108",
        "building_key": "marlow-commons",
        "rent": 2790,
        "clauses": [
            "parties",
            "term",
            "deposit_ok",
            "fees_nonrefundable",
            "early_term_fee",
            "auto_renew",
            "late_fee_high",
            "maintenance_ok",
            "entry_ok",
            "guest_limits",
            "pets_fee",
            "utilities_rubs",
            "moveout_cleaning",
        ],
    },
    "lease_4_coleman_yards_control": {
        "title": "Residential Lease — Coleman Yards, Unit 522",
        "building_key": "coleman-yards",
        "rent": 3300,
        "clauses": [
            "parties",
            "term",
            "deposit_high",
            "rent_increase_cap_breaker",
            "late_fee_ok",
            "maintenance_ok",
            "entry_no_notice",
            "sublet_ban",
            "guest_limits",
            "parking_fee",
            "insurance_req",
            "attorneys_fees_onesided",
            "moveout_ok",
        ],
    },
    "lease_5_japantown_walk_waivers": {
        "title": "Residential Lease — Japantown Walk, Unit 204",
        "building_key": "japantown-walk",
        "rent": 2650,
        "clauses": [
            "parties",
            "term",
            "deposit_ok",
            "early_term_fee",
            "late_fee_ok",
            "maintenance_shift",
            "entry_ok",
            "liability_waiver",
            "arbitration_jury_waiver",
            "joint_several",
            "insurance_req",
            "moveout_ok",
        ],
    },
    "lease_6_el_camino_kitchen_sink": {
        "title": "Residential Lease — El Camino Lofts, Unit 117",
        "building_key": "el-camino-lofts",
        "rent": 2550,
        "clauses": [
            "parties",
            "term",
            "deposit_high",
            "fees_nonrefundable",
            "early_term_fee",
            "auto_renew",
            "rent_increase_cap_breaker",
            "late_fee_high",
            "maintenance_shift",
            "entry_no_notice",
            "sublet_ban",
            "guest_limits",
            "pets_fee",
            "utilities_rubs",
            "liability_waiver",
            "attorneys_fees_onesided",
            "arbitration_jury_waiver",
            "moveout_cleaning",
            "as_is",
        ],
    },
}


LEASE_SPECS: dict[str, LeaseSpec] = {k: _spec(v) for k, v in _RAW_SPECS.items()}
