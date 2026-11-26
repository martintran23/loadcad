"""Cited material cards.

Aluminum numbers are the Aluminum Association typical values reproduced on the
ASM MatWeb 6061-T6 sheet. That sheet marks them "NOT FOR DESIGN". Printed-plastic
numbers are from the named Prusament datasheets. Those sheets do not publish
Poisson's ratio, so the printed cards cannot be solved until a cited ratio exists.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from loadcad.units import gpa_to_mpa, kg_per_m3_to_tonne_per_mm3


class MaterialError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MaterialCard:
    material_id: str
    version: int
    display_name: str
    youngs_modulus_mpa: float
    poissons_ratio: float | None
    density_tonne_per_mm3: float
    allowable_stress_mpa: float
    allowable_basis: str
    isotropy: str
    source: str
    limitations: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def require_solvable(self) -> None:
        if self.poissons_ratio is None:
            raise MaterialError(
                "request_invalid",
                f"{self.material_id} has no cited Poisson's ratio and cannot be solved",
            )
        if not -1.0 < self.poissons_ratio < 0.5:
            raise MaterialError(
                "request_invalid",
                f"{self.material_id} Poisson's ratio must be greater than -1 and less than 0.5",
            )
        if self.allowable_stress_mpa <= 0.0 or self.youngs_modulus_mpa <= 0.0:
            raise MaterialError("request_invalid", f"{self.material_id} has a nonpositive material number")
        if self.allowable_basis not in {"tensile_yield", "tensile_strength", "specified_allowable"}:
            raise MaterialError("request_invalid", f"unknown allowable basis {self.allowable_basis}")
        if self.isotropy != "isotropic":
            raise MaterialError("request_invalid", "only isotropic cards can be solved")


ALUMINUM_6061_T6 = MaterialCard(
    material_id="aluminum_6061_t6",
    version=1,
    display_name="Aluminum 6061-T6, AA typical",
    youngs_modulus_mpa=gpa_to_mpa(68.9),
    poissons_ratio=0.33,
    density_tonne_per_mm3=kg_per_m3_to_tonne_per_mm3(2700.0),
    allowable_stress_mpa=276.0,
    allowable_basis="tensile_yield",
    isotropy="isotropic",
    source=(
        "ASM MatWeb, Aluminum 6061-T6; 6061-T651, bassnum MA6061t6, "
        "read 2026-11-24. Values marked AA; Typical: tensile yield 276 MPa, "
        "modulus 68.9 GPa, density 2.70 g/cc. Poisson's ratio 0.33 is marked "
        "estimated from trends in similar aluminum alloys. "
        "https://asm.matweb.com/search/SpecificMaterial.asp?bassnum=MA6061t6"
    ),
    limitations=(
        "These are Aluminum Association typical values. The same sheet says "
        "AA data are not for design. This is not an MMPDS A-basis or B-basis "
        "allowable, and the product form and thickness are not specified. "
        "Poisson's ratio was estimated by the sheet from similar alloys."
    ),
)

PRUSAMENT_PLA = MaterialCard(
    material_id="prusament_pla",
    version=1,
    display_name="Prusament PLA, printed-specimen sheet",
    youngs_modulus_mpa=gpa_to_mpa(2.3),
    poissons_ratio=None,
    density_tonne_per_mm3=kg_per_m3_to_tonne_per_mm3(1240.0),
    allowable_stress_mpa=17.0,
    allowable_basis="specified_allowable",
    isotropy="isotropic",
    source=(
        "Prusa Polymers, Technical datasheet Prusament PLA, version 1.1, "
        "last update 16-02-2022. Horizontal tensile modulus 2.3 GPa and "
        "horizontal tensile yield 51 MPa are ISO 527-1 printed-specimen values. "
        "Interlayer adhesion 17 MPa is a Prusa Polymers method, not ISO 527. "
        "Density 1.24 g/cm3 is ISO 1183. "
        "https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf"
    ),
    limitations=(
        "The allowable is the published interlayer adhesion, 17 MPa, because "
        "the model is an isotropic solid and does not know the print direction. "
        "The same sheet reports a horizontal tensile yield of 51 MPa, which is "
        "not the allowable used here. The sheet does not give Poisson's ratio, "
        "so this card cannot be solved. The printed coupon is not the simulated "
        "solid. Values depend on print settings."
    ),
)

PRUSAMENT_PETG = MaterialCard(
    material_id="prusament_petg",
    version=1,
    display_name="Prusament PETG, printed-specimen sheet",
    youngs_modulus_mpa=gpa_to_mpa(1.5),
    poissons_ratio=None,
    density_tonne_per_mm3=kg_per_m3_to_tonne_per_mm3(1270.0),
    allowable_stress_mpa=18.0,
    allowable_basis="specified_allowable",
    isotropy="isotropic",
    source=(
        "Prusa Polymers, Technical datasheet Prusament PETG, version 1.1, "
        "last update 16-02-2022. Horizontal tensile modulus 1.5 GPa and "
        "horizontal tensile yield 47 MPa are ISO 527-1 printed-specimen values. "
        "Interlayer adhesion 18 MPa is a Prusa Polymers method. Density 1.27 g/cm3 "
        "is ISO 1183. "
        "https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf"
    ),
    limitations=(
        "The allowable is the published interlayer adhesion, 18 MPa, because "
        "the model is an isotropic solid and does not know the print direction. "
        "The same sheet reports a horizontal tensile yield of 47 MPa, which is "
        "not the allowable used here. The sheet does not give Poisson's ratio, "
        "so this card cannot be solved. The printed coupon is not the simulated "
        "solid. Values depend on print settings."
    ),
)

CARDS = {
    card.material_id: card
    for card in (ALUMINUM_6061_T6, PRUSAMENT_PLA, PRUSAMENT_PETG)
}


def get_card(material_id: str) -> MaterialCard:
    try:
        return CARDS[material_id]
    except KeyError as exc:
        raise MaterialError("request_invalid", f"unknown material {material_id}") from exc
