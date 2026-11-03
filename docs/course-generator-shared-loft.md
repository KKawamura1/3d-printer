# Issue #37: independent loft geometry from configuration

The historical PR scripts were nearly identical generators with different
constants. Their common operations now live in
brickcad.course_loft_family.build_course.

Inputs: centreline (straight / sharp R16 / gentle R48), level/19.2-mm
smoothstep downhill floor, open/tunnel enclosure, XZ reflection and visible
standard 3.0-mm/0.4-mm readable engraving. The roofed sharp downhill tunnel
uses a true circular entry/exit with a 1-mm lip, unlike early pointed mouths.

Construction sequence: swept loft footprint -> underside receiver -> passage
subtraction -> E31-05 beads/slots for **complete** lower tubes only -> clipped
roof studs (rooted, not floating) -> unmarked mirror -> final mark.

The engine imports brickcad shared standards, E31 geometry helper and CadQuery,
but DOES NOT import or call original parts.*.design builders or exporters.
Reference PR pins in registry.json serve as *test oracles only*, not production
dependencies. No individual source checkout happens in production for these
configured models.

Verified recipe coverage in the first shared family:
GC01-V5, D02-V4, SC03-V5, SC05-V1,
SD01-V4, SD02-V4, SD03-V11, SD04-V10.

The other 12 models still require independent family implementations. The
earlier PR-pinned CAD dispatcher for those models remains a temporary fallback
and MUST NOT be described as genuine configurable generation.

Parity must compare the new *unmarked* BRep with fixed original BRep in both
directions. Engraved solids must additionally be checked for upright readable
marking on both handednesses. Passing CAD mesh checks alone is NOT parity.
