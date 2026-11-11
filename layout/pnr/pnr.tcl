# layout/pnr/pnr.tcl -- Encounter (EDI 13.1) place & route mot khoi. Goi tu layout/pnr/run_pnr.sh:
#   BLK=DIV8 UTIL=0.7 W=<repo> encounter -nowin -init layout/pnr/pnr.tcl
# Vao: layout/pnr/v/$BLK.v (prep.py), gpdk090.lef + layout/pnr/lef/cells.lef. Ra (thu muc chay):
#   $BLK.gds (gop GDS cell), $BLK.def, rpt_*.txt. Khong co thu vien thoi gian -> place/route khong theo tre.
set W   $env(W)
set BLK $env(BLK)
set UTIL [expr {[info exists env(UTIL)] ? $env(UTIL) : 0.7}]
set TOPL [expr {[info exists env(TOPL)] ? $env(TOPL) : 6}]
set PDK /home/buet/cadence/gpdk090_v4.6

set init_lef_file   "$W/layout/pnr/lef/tech.lef $W/layout/pnr/lef/cells.lef"
set init_verilog    "$W/layout/pnr/v/$BLK.v"
set init_top_cell   $BLK
set init_pwr_net    VDD
set init_gnd_net    VSS
init_design

# Hang cell cao 2.76; hang le lat (MX) de dung chung ray. Le 3 um cho vong nguon.
floorPlan -site CoreSite -r 1.0 $UTIL 3.0 3.0 3.0 3.0
globalNetConnect VDD -type pgpin -pin VDD -inst * -override
globalNetConnect VSS -type pgpin -pin VSS -inst * -override

# Thu: dat cell truoc khi ve nguon (ENCSP-270 khi ray sroute co truoc).
# PAD="BOOTH_SEL BOOTH_ENC": chua 2 site ben phai cell nhieu chan (giam ket M2 o diem vao chan)
if {[info exists env(PAD)]} { foreach c $env(PAD) { specifyCellPad $c 2 } }
# Chan IO de placeDesign tu dat. Da thu editPin (vao trai / ra phai, M3): route M2 o BOOTH xau hon (7..11 loi SP).
# placeIoPins co the chong 2 chan (ALU_TOP UTIL 0.72: Y_11/Y_12 -> LVS sai) -> doi UTIL (ALU_TOP sach o 0.66).
setPlaceMode -timingDriven false -placeIoPins true
placeDesign -noPrePlaceOpt
checkPlace rpt_place.txt
addFiller -cell {FILL8 FILL4 FILL2 FILL1} -prefix FIL

# Vong nguon Metal3 (ngang) / Metal2 (doc) quanh loi, noi ray M1 cua tung hang vao vong.
addRing -nets {VDD VSS} -type core_rings -layer {top Metal3 bottom Metal3 left Metal2 right Metal2} \
    -width 0.6 -spacing 0.4 -offset 0.6
sroute -connect {corePin} -nets {VDD VSS}
# Pin VDD/VSS tren doan vong Metal3 dau tien -> streamOut ghi nhan (LVS can ten net nguon).
foreach n {VDD VSS} {
  set net [dbGet -p top.nets.name $n]
  foreach w [dbGet $net.sWires] {
    set ly [dbGet $w.layer.name]
    if {$ly == "M3" || $ly == "Metal3"} {
      set b [lindex [dbGet $w.box] 0]
      puts "PNR_PGPIN $n $b [catch {createPGPin $n -net $n -geom $ly [lindex $b 0] [lindex $b 1] [lindex $b 2] [lindex $b 3]} e] $e"
      break
    }
  }
}

setNanoRouteMode -routeTopRoutingLayer $TOPL -routeBottomRoutingLayer 2 -routeWithTimingDriven false \
    -drouteFixAntenna false
globalDetailRoute
# NanoRoute de lai khe giua hai via cung net (M2/M3 < 0.14, Assura METAL2.SP.1.1): lap khe cung net
puts "PNR_FILLNOTCH [catch {fillNotch} e] $e"

verifyGeometry -report rpt_geom.txt
verifyConnectivity -type all -report rpt_conn.txt
reportGateCount -outfile rpt_gates.txt
summaryReport -noHtml -outfile rpt_summary.txt
set box [dbGet top.fPlan.box]
puts "PNR_BOX $BLK $box"
defOut -floorplan -netlist -routing $BLK.def
set gds {}
foreach l {ALU_CELLS_A ALU_STUB_B ALU_CELLS_B ALU_CELLS_C ALU_CELLS_D ALU_CELLS_P} { lappend gds /mnt/hgfs/Share/VLSI_work/out/gds/$l.gds }
streamOut $BLK.gds -mapFile $PDK/soce/soce_gds.map -libName ALU_BLK -structureName $BLK -merge $gds \
    -units 2000 -mode ALL
puts "PNR_DONE $BLK"
exit
