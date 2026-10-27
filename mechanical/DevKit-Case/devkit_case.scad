// ESP32 Marauder v4 case for a generic 30-pin ESP32 DevKit (USB-C, CH340) + 2.8" ILI9341 SPI screen.
// Three parts: "shell" (front bezel + walls + rails), "plate" (ESP32 tray, drops onto the rails) and
// "lid" (back cover + snap arms + screen pillars). All three print without supports.
//
// Coordinates: X across the width (centered), Y along the length (Y=0 is the USB end),
// Z from the front face (Z=0, the screen side) to the back.
//
// Render one part:  openscad -D 'part="shell"' -o shell.stl devkit_case.scad
//   part = "shell" | "plate_print" | "lid_print" | "assembly"   (plate / lid are the as-fitted orientation for "plate"/"lid")

part = "assembly";
$fn = 32;

// ---- measured / assumed dimensions (mm) -------------------------------------------------
// Screen module (Marauder Screen PCB Measurements.png + your 12 mm thickness)
scr_w = 50;            // PCB width
scr_l = 86;            // PCB length
scr_t = 12;            // total thickness, glass front to rear-most part (you measured 1.2 cm)
scr_pcb_back = 5.7;    // measured: glass front to the back face of the PCB
scr_hole = 3;          // mounting hole centres are 3 mm in from each PCB edge
active_w = 43.2;       // ILI9341 2.8" active area (portrait)
active_l = 57.6;
glass_top = 6.4;       // PCB top edge to glass top edge
glass_len = 69.2;      // glass length

// ESP32 dev board (ESP32-WROOM-32 DevKitC style, micro-USB). ASSUMED ~54.4 x 27.9 mm; adjust to your board.
// The board lies ACROSS the case (its length along X) with the micro-USB facing the left wall,
// the same side as the SD slot, component side toward the screen, pins toward the back.
esp_l = 54.4;
esp_w = 27.9;
esp_pcb_t = 1.6;
esp_comp_h = 4.0;      // tallest part on the component side (module, buttons) ~3.3 + margin
esp_row = 25.4;        // distance between the two pin rows
hdr_plastic = 2.5;     // black plastic spacer of the pin header
usb_w = 9.5;           // micro-USB cutout (plug metal is ~7 x 2.5; the moulded plug stays outside the wall)
usb_h = 4.6;

// Case
wall = 2.0;
clr = 0.4;             // clearance around the screen
front_t = 1.6;         // front plate thickness
slack_far = 3.2;       // extra room at the header end of the screen for dupont plugs
z_seam = 32;           // shell/lid split plane
z_total = 41;          // overall depth (room for 14 mm dupont plugs + wire bend behind the ESP32)
back_t = 2.0;

esp_x_gap = 1.2;                       // PCB end to the left wall (the micro-USB shell sticks out ~1 mm past the PCB)
rim_t = 1.6;                           // rim around the ESP32 on the plate
iw = esp_x_gap + esp_l + 0.4 + rim_t + 0.3;   // inner width, set by the ESP32 lying across the case (~58 mm)
il = scr_l + 2 * clr + slack_far;      // inner length
ow = iw + 2 * wall;                    // outer width
ol = il + 2 * wall;                    // outer length

scr_y0 = wall + clr;                   // screen top edge inside the case
scr_cx = -iw/2 + clr + scr_w/2;        // screen sits against the left wall (SD card side); a filler rib takes up the rest

// ESP32 plate: board component side faces the screen, pins point to the back
scr_rear = scr_pcb_back + front_t + 2.0;              // rear of screen body incl. ICs (+2 mm assumed)
esp_lift = 2.5;                                       // keeps the micro-USB cutout clear of the SD-card opening below it
esp_pcb_front = scr_rear + 0.5 + esp_comp_h + esp_lift;
plate_z0 = esp_pcb_front + esp_pcb_t;                 // board back face rests on the plate
plate_t = hdr_plastic;
esp_x0 = -iw/2 + esp_x_gap;                           // USB end of the board (left wall side)
esp_x1 = esp_x0 + esp_l;
esp_yc = scr_y0 + scr_l/2;                            // board centred along the screen's length
esp_y0 = esp_yc - esp_w/2;
esp_y1 = esp_yc + esp_w/2;
usb_z = esp_pcb_front - 1.6;                          // port centre height

// micro-SD access on the screen module (slot is on the back of the PCB, card enters from a long edge)
sd_side = -1;                          // -1 = left wall, +1 = right wall (looking at the glass, header end at the bottom)
sd_from_hdr = 48.5;                    // ESTIMATED from a photo: slot centre, mm from the header edge of the screen
sd_len = 27;                           // opening length: a full-size SD card in an adapter is ~24 mm wide
sd_h = 5.0;                            // opening height (card is ~2.1 mm thick; extra for the height uncertainty)
sd_z0 = front_t + scr_pcb_back - 1.5;  // starts a little in front of the back face of the screen PCB

// ESP32 plate rails (45 degree underside, so no supports)
ledge_w = 2.6;
ledge_y0 = 9;                          // start after the screen-pillar clearance
plate_y0 = esp_y0 - 3;
plate_y1 = esp_y1 + 3;
plate_clr = 0.3;

// snap-fit
lip_t = 1.6;
lip_z0 = plate_z0 + plate_t + 0.6;   // lip starts just behind the ESP32 plate
arm_w = 8;
arm_ys = [28, 62];
bump = 0.9;
win_z0 = lip_z0 + 0.5; win_z1 = lip_z0 + 4.5;

module box(x0, y0, z0, x1, y1, z1) {
    translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, z1 - z0]);
}

// ---------------------------------------------------------------------------------------
module shell() {
    difference() {
        box(-ow/2, 0, 0, ow/2, ol, z_seam);
        // cavity
        box(-iw/2, wall, front_t, iw/2, wall + il, z_seam + 1);
        // display window (centred on the glass)
        translate([scr_cx, scr_y0 + glass_top + glass_len/2, -1])
            translate([-(active_w + 1.8)/2, -(active_l + 1.8)/2, 0])
                cube([active_w + 1.8, active_l + 1.8, front_t + 2]);
        // micro-USB cutout in the left wall, in line with the board's port
        box(-ow/2 - 1, esp_yc - usb_w/2, usb_z - usb_h/2, -iw/2 + 1, esp_yc + usb_w/2, usb_z + usb_h/2);
        // snap windows in the long walls
        for (s = [-1, 1]) for (y = arm_ys)
            box(s > 0 ? iw/2 - 1 : -ow/2 - 1, y - arm_w/2 - 0.3, win_z0,
                s > 0 ? ow/2 + 1 : -iw/2 + 1, y + arm_w/2 + 0.3, win_z1);
        // micro-SD opening in the left wall: a plain rectangle wide enough for a full-size card (the roof bridges ~27 mm)
        sd_yc = scr_y0 + scr_l - sd_from_hdr;
        box(sd_side > 0 ? iw/2 - 1 : -ow/2 - 1, sd_yc - sd_len/2, sd_z0,
            sd_side > 0 ? ow/2 + 1 : -iw/2 + 1, sd_yc + sd_len/2, sd_z0 + sd_h);
    }
    // filler rib along the right side of the screen, so the screen can't slide sideways
    box(scr_cx + scr_w/2 + 0.4, wall, front_t, iw/2, wall + il, front_t + scr_pcb_back);
    // rails the ESP32 plate rests on (45 degree underside) + stop tabs at both ends
    for (sx = [-1, 1]) {
        difference() {
            translate([0, plate_y1 + 2.5, 0]) rotate([90, 0, 0]) linear_extrude(plate_y1 + 2.5 - ledge_y0)
                polygon([[sx * (iw/2 + 0.01), plate_z0], [sx * (iw/2 - ledge_w), plate_z0], [sx * (iw/2 + 0.01), plate_z0 - ledge_w]]);
            // keep the left rail clear of the USB plug
            if (sx < 0) box(-iw/2 - 1, esp_yc - usb_w/2 - 1, 0, -iw/2 + ledge_w + 1, esp_yc + usb_w/2 + 1, plate_z0 + 1);
        }
        box(sx > 0 ? iw/2 - ledge_w : -iw/2 - 0.01, plate_y1 + 0.3, plate_z0,
            sx > 0 ? iw/2 + 0.01 : -iw/2 + ledge_w, plate_y1 + 2.5, plate_z0 + plate_t);
        box(sx > 0 ? iw/2 - ledge_w : -iw/2 - 0.01, plate_y0 - 2.5, plate_z0,
            sx > 0 ? iw/2 + 0.01 : -iw/2 + ledge_w, plate_y0 - 0.3, plate_z0 + plate_t);
    }
}

// ---------------------------------------------------------------------------------------
// ESP32 tray: board (chip side toward the screen) rests on its front face, pin headers pass through the slots.
module esp_plate() {
    difference() {
        union() {
            box(-iw/2 + plate_clr, plate_y0, plate_z0, iw/2 - plate_clr, plate_y1, plate_z0 + plate_t);
            // rim around the board footprint (open at the USB end: the board's end sits at the wall)
            difference() {
                box(esp_x0 - 0.2, esp_y0 - 0.4 - rim_t, plate_z0 - esp_pcb_t, esp_x1 + 0.4 + rim_t, esp_y1 + 0.4 + rim_t, plate_z0 + 0.01);
                box(esp_x0 - 1, esp_y0 - 0.4, plate_z0 - esp_pcb_t - 1, esp_x1 + 0.4, esp_y1 + 0.4, plate_z0 + 1);
            }
        }
        // slots for the two pin-header plastics (whole board length so pin positions don't matter)
        for (s = [-1, 1])
            box(esp_x0 + 0.6, esp_yc + s * esp_row/2 - 1.5, plate_z0 - 3, esp_x1 - 0.6, esp_yc + s * esp_row/2 + 1.5, plate_z0 + plate_t + 1);
        // clearance for the lid's screen pillars (only the ones that fall inside the plate)
        for (s = [-1, 1]) translate([scr_cx + s * (scr_w/2 - scr_hole), scr_y0 + scr_hole, plate_z0 - 3])
            cylinder(d = 7, h = plate_t + 6);
    }
}

// ---------------------------------------------------------------------------------------
module lid() {
    lo_w = iw - 0.6;   // lip outer size (0.3 mm clearance each side)
    lo_l = il - 0.6;
    difference() {
        union() {
            // outer skin, flush with the shell
            // (the cavity is the lip's inner size, so the lip stands on solid wall and prints without supports)
            difference() {
                box(-ow/2, 0, z_seam, ow/2, ol, z_total);
                box(-lo_w/2 + lip_t, wall + 0.3 + lip_t, z_seam - 1, lo_w/2 - lip_t, wall + 0.3 + lo_l - lip_t, z_total - back_t);
            }
            // lip that slides into the shell
            difference() {
                box(-lo_w/2, wall + 0.3, lip_z0, lo_w/2, wall + 0.3 + lo_l, z_seam + 0.01);
                box(-lo_w/2 + lip_t, wall + 0.3 + lip_t, lip_z0 - 1, lo_w/2 - lip_t, wall + 0.3 + lo_l - lip_t, z_seam + 1);
            }
            // snap bumps on the arms
            for (s = [-1, 1]) for (y = arm_ys) snap_bump(s, y, lo_w);
            // pillars pressing on the screen PCB corners
            for (sx = [-1, 1]) for (yy = [scr_y0 + scr_hole, scr_y0 + scr_l - scr_hole])
                translate([scr_cx + sx * (scr_w/2 - scr_hole), yy, front_t + scr_pcb_back])
                    cylinder(d = 4.8, h = z_total - back_t - (front_t + scr_pcb_back) + 0.01);
        }
        // arm slits (U-shape leaves a cantilever attached at the seam)
        for (s = [-1, 1]) for (y = arm_ys) {
            for (dy = [-1, 1])
                box(s > 0 ? lo_w/2 - lip_t - 0.5 : -lo_w/2 - 0.5, y + dy * (arm_w/2 + 0.6) - 0.6, lip_z0 - 1,
                    s > 0 ? lo_w/2 + 0.5 : -lo_w/2 + lip_t + 0.5, y + dy * (arm_w/2 + 0.6) + 0.6, z_seam - 1.0);
        }
    }
}

module snap_bump(s, y, lo_w) {
    // wedge: ramp on the front (insertion) side, square shoulder on the back side
    x_in = s * (lo_w/2 - lip_t/2);
    x_out = s * (lo_w/2 + bump);
    hull() {
        translate([x_in, y - arm_w/2, win_z0 + 0.5]) cube([0.01, arm_w, 0.01]);
        translate([x_out, y - arm_w/2, win_z0 + 1.5]) cube([0.01, arm_w, 0.01]);
        translate([x_out, y - arm_w/2, win_z1 - 0.5]) cube([0.01, arm_w, 0.01]);
        translate([x_in, y - arm_w/2, win_z1 - 0.5]) cube([0.01, arm_w, 0.01]);
    }
}

// ---------------------------------------------------------------------------------------
// dummy parts, used only to check clearances in the assembly view
module dummy_screen() {
    color("green") translate([scr_cx - scr_w/2, scr_y0, front_t]) cube([scr_w, scr_l, scr_pcb_back]);
    color("navy") translate([scr_cx - scr_w/2, scr_y0 + glass_top, front_t]) cube([scr_w, glass_len, 0.1]);
    // header + plugs at the far edge
    color("gray") translate([scr_cx - 16.5, scr_y0 + scr_l - 3, front_t + scr_pcb_back]) cube([33, 2.6, scr_t - scr_pcb_back]);
    // SD card in its adapter, sticking out of the left edge (24 x 32 x 2.1)
    color("blue") translate([scr_cx - scr_w/2 - 17, scr_y0 + scr_l - sd_from_hdr - 12, sd_z0 + (sd_h - 2.1)/2]) cube([32, 24, 2.1]);
}
module dummy_esp() {
    color("red") translate([esp_x0, esp_y0, plate_z0 - esp_pcb_t]) cube([esp_l, esp_w, esp_pcb_t]);
    color("orange") translate([esp_x0 + 14, esp_y0 + 4, plate_z0 - esp_pcb_t - esp_comp_h]) cube([24, esp_w - 8, esp_comp_h]);
    color("silver") translate([esp_x0 - 1, esp_yc - 4, usb_z - 1.3]) cube([7, 8, 2.6]);
    for (s = [-1, 1]) color("black") translate([esp_x0 + 2, esp_yc + s * esp_row/2 - 1.27, plate_z0]) cube([38, 2.54, hdr_plastic]);
}

if (part == "shell") shell();
else if (part == "plate") esp_plate();
else if (part == "plate_print") translate([0, plate_y1, plate_z0 + plate_t]) rotate([180, 0, 0]) esp_plate();   // back face on the bed, rim up
else if (part == "lid") lid();
else if (part == "lid_print") translate([0, ol, z_total]) rotate([180, 0, 0]) lid();   // back plate on the bed
else if (part == "print") {
    shell();
    translate([ow + 10, 0, 0]) translate([0, ol, z_total]) rotate([180, 0, 0]) lid();
}
else if (part == "ghost") {      // the parts the case was designed around, in the shell's coordinates (for the STL viewer's ghost overlay)
    dummy_screen();
    dummy_esp();
}
else if (part == "assembly") {
    color("lightblue", 0.6) shell();
    color("khaki", 0.8) esp_plate();
    color("salmon", 0.6) lid();
    dummy_screen();
    dummy_esp();
}
