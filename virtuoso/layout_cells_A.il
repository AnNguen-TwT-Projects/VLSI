;; virtuoso/layout_cells_A.il -- layout views of ALU_CELLS_A, gpdk090.
;; Idempotent: (re)creates only the "layout" view of each cell; schematic/symbol untouched.
;; Run in the VM (normally via virtuoso/run_layout_cell.sh):
;;   cd ~/ALU_PROJ && virtuoso -nograph -restore <repo>/virtuoso/layout_cells_A.il < /dev/null
;; Template, all values in um:
;;   height 2.76; column pitch 0.27, column k at x = 0.27*(k+1), width = 0.27*(ncols+1)
;;   even columns = diffusion nodes (contacts), odd columns = poly gates
;;   VSS rail Metal1 y 0..0.24 over P+ tap, VDD rail y 2.52..2.76 over N+ tap
;;   nMOS row centred y 0.64, pMOS row centred y 2.00, Nwell y >= 1.38
;;   input pins: Metal1 0.18x0.40 pads on the gate column, y 1.12..1.52
;;   M1 routing tracks: Tn y 0.94, Tp y 1.70 (between the rows)

laLib = "ALU_CELLS_A"
laG = 0.27
laH = 2.76
laYN = 0.64
laYP = 2.00
laYTn = 0.94
laYTp = 1.70
laYIn = 1.32
laYVSS = 0.12
laYVDD = 2.64
laErr = 0

procedure(laX(k) laG * (k + 1))
procedure(laSnap(v) round(v * 2000.0) / 2000.0)

procedure(laBox(cv lyr purp x1 y1 x2 y2)
  let((fig)
    fig = dbCreateRect(cv list(lyr purp)
            list(list(laSnap(min(x1 x2)) laSnap(min(y1 y2)))
                 list(laSnap(max(x1 x2)) laSnap(max(y1 y2)))))
    unless(fig
      printf("LA_ERROR rect %s %s failed in %s\n" lyr purp cv~>cellName)
      laErr = laErr + 1)
    fig))

procedure(laR(cv lyr x1 y1 x2 y2) laBox(cv lyr "drawing" x1 y1 x2 y2))

procedure(laLabel(cv name x y)
  let((lb)
    lb = car(errset(dbCreateLabel(cv list("Metal1" "label") list(laSnap(x) laSnap(y))
                      name "centerCenter" "R0" "stick" 0.1)))
    unless(lb
      lb = dbCreateLabel(cv list("Metal1" "pin") list(laSnap(x) laSnap(y))
             name "centerCenter" "R0" "stick" 0.1))
    lb))

;; Metal1 pin shape + terminal + label (Assura: pinText("Metal1") and textToPin Metal1/label)
procedure(laPin(cv name dir x1 y1 x2 y2)
  let((fig net)
    fig = laBox(cv "Metal1" "pin" x1 y1 x2 y2)
    net = or(dbFindNetByName(cv name) dbCreateNet(cv name))
    unless(dbFindTermByName(cv name) dbCreateTerm(net name dir))
    dbCreatePin(net fig name)
    laLabel(cv name (x1 + x2) / 2.0 (y1 + y2) / 2.0)))

;; rails, taps, implants, Nwell, boundary, VDD/VSS pins; returns cell width
procedure(laFrame(cv ncols)
  let((w x)
    w = laG * (ncols + 1)
    ;; tiep xuc tap nam TREN bien cell (y 0 va laH): hai hang lat dung chung ray -> tiep xuc trung nhau
    ;; hoac cach 0.27 ngang (CONT.SP.1 0.14); oxide/implant/Metal1 tap loi ra ngoai bien 0.12.
    laR(cv "Metal1" 0 -0.06 w 0.24)
    laR(cv "Metal1" 0 laH - 0.24 w laH + 0.06)
    laR(cv "Oxide" 0 -0.12 w 0.24)
    laR(cv "Pimp" -0.02 -0.14 w + 0.02 0.26)
    laR(cv "Oxide" 0 laH - 0.24 w laH + 0.12)
    laR(cv "Nimp" -0.02 laH - 0.34 w + 0.02 laH + 0.14)
    laR(cv "Nwell" -0.12 1.38 w + 0.12 laH + 0.24)
    laR(cv "Nimp" 0 0.26 w 1.00)
    laR(cv "Pimp" 0 1.50 w laH - 0.34)
    for(k 0 ncols - 1
      x = laX(k)
      laR(cv "Cont" x - 0.06 -0.06 x + 0.06 0.06)
      laR(cv "Cont" x - 0.06 laH - 0.06 x + 0.06 laH + 0.06))
    laPin(cv "VSS" "inputOutput" 0 0 w 0.24)
    laPin(cv "VDD" "inputOutput" 0 laH - 0.24 w laH)
    laBox(cv "prBoundary" "drawing" 0 0 w laH)
    w))

;; one diffusion row: items per column, even = "c" (contact) | "n" (no contact), odd = gate W
procedure(laStrip(cv items yc)
  let((n x w h)
    n = length(items)
    for(k 0 n - 1
      x = laX(k)
      if(oddp(k) then
        w = nth(k items)
        laR(cv "Oxide" x - 0.15 yc - w / 2.0 x + 0.15 yc + w / 2.0)
      else
        h = max(if(k > 0 nth(k - 1 items) 0.0) if(k < n - 1 nth(k + 1 items) 0.0))
        when(equal(nth(k items) "c") h = max(h 0.24))
        laR(cv "Oxide" x - 0.12 yc - h / 2.0 x + 0.12 yc + h / 2.0)
        when(equal(nth(k items) "c")
          laR(cv "Cont" x - 0.06 yc - 0.06 x + 0.06 yc + 0.06)
          laR(cv "Metal1" x - 0.06 yc - 0.12 x + 0.06 yc + 0.12))))))

;; gate column k: poly line through both rows, poly contact + Metal1 input pin pad
procedure(laGate(cv k name)
  let((x)
    x = laX(k)
    laR(cv "Poly" x - 0.05 laYN - 0.30 x + 0.05 laYP + 0.42)
    laR(cv "Poly" x - 0.10 laYIn - 0.12 x + 0.10 laYIn + 0.12)
    laR(cv "Cont" x - 0.06 laYIn - 0.06 x + 0.06 laYIn + 0.06)
    laR(cv "Metal1" x - 0.09 laYIn - 0.20 x + 0.09 laYIn + 0.20)
    laPin(cv name "input" x - 0.09 laYIn - 0.20 x + 0.09 laYIn + 0.20)))

;; wires: ("v" k y1 y2) vertical M1 on column k (centre line, 0.12 wide, ends +0.06)
;;        ("h" k1 k2 y)  horizontal M1 track; ("pad" k y) 0.26x0.28 M1 via landing
;;        ("via" x y) Via1 0.14; ("m2" x1 x2 y) Metal2 0.15 tall
procedure(laWire(cv wr)
  let((kind)
    kind = car(wr)
    cond(
      (equal(kind "v")
        laR(cv "Metal1" laX(nth(1 wr)) - 0.06 min(nth(2 wr) nth(3 wr)) - 0.06
                        laX(nth(1 wr)) + 0.06 max(nth(2 wr) nth(3 wr)) + 0.06))
      (equal(kind "h")
        laR(cv "Metal1" laX(min(nth(1 wr) nth(2 wr))) - 0.06 nth(3 wr) - 0.06
                        laX(max(nth(1 wr) nth(2 wr))) + 0.06 nth(3 wr) + 0.06))
      (equal(kind "pad")
        laR(cv "Metal1" laX(nth(1 wr)) - 0.13 nth(2 wr) - 0.14 laX(nth(1 wr)) + 0.13 nth(2 wr) + 0.14))
      (equal(kind "via")
        laR(cv "Via1" nth(1 wr) - 0.07 nth(2 wr) - 0.07 nth(1 wr) + 0.07 nth(2 wr) + 0.07))
      (equal(kind "m2")
        laR(cv "Metal2" nth(1 wr) nth(3 wr) - 0.075 nth(2 wr) nth(3 wr) + 0.075))
      (t printf("LA_ERROR bad wire %L\n" wr) laErr = laErr + 1))))

procedure(laReport(cv w)
  printf("LA_CELL %-9s W=%.3f H=%.3f area=%.4f um2 bBox=%L\n" cv~>cellName w laH w * laH cv~>bBox))

;; leaf cell: nItems/pItems per column, gates ((k name) ...), outs ((name k) ...)
procedure(laCell(name nItems pItems gates wires outs)
  let((cv w ncols)
    ncols = length(nItems)
    cv = dbOpenCellViewByType(laLib name "layout" "maskLayout" "w")
    w = laFrame(cv ncols)
    laStrip(cv nItems laYN)
    laStrip(cv pItems laYP)
    foreach(g gates laGate(cv car(g) cadr(g)))
    foreach(wr wires laWire(cv wr))
    foreach(o outs
      laPin(cv car(o) "output" laX(cadr(o)) - 0.06 laYIn - 0.20 laX(cadr(o)) + 0.06 laYIn + 0.20))
    dbSave(cv)
    laReport(cv w)
    cv))

;; hierarchical cell: parts ((instName cell xOffset) ...), pins ((name dir subCellX colK) ...)
;; dir input -> 0.18 wide gate pad, output -> 0.12 wide output wire (same spots as the leaf pins)
procedure(laHier(name parts pins wires)
  let((cv w x hw master)
    cv = dbOpenCellViewByType(laLib name "layout" "maskLayout" "w")
    ;; width = right edge of the last part's prBoundary
    w = 0.0
    foreach(p parts
      master = dbOpenCellViewByType(laLib cadr(p) "layout" nil "r")
      dbCreateInst(cv master car(p) list(caddr(p) 0.0) "R0")
      foreach(s master~>shapes
        when(s~>layerName == "prBoundary"
          w = max(w caddr(p) + caadr(s~>bBox)))))
    foreach(pn pins
      x = nth(2 pn) + laX(nth(3 pn))
      hw = if(equal(nth(1 pn) "input") 0.09 0.06)
      laPin(cv car(pn) nth(1 pn) x - hw laYIn - 0.20 x + hw laYIn + 0.20))
    foreach(wr wires laWire(cv wr))
    laPin(cv "VSS" "inputOutput" 0 0 w 0.24)
    laPin(cv "VDD" "inputOutput" 0 laH - 0.24 w laH)
    laBox(cv "prBoundary" "drawing" 0 0 w laH)
    dbSave(cv)
    laReport(cv w)
    cv))

procedure(laMain()
  let((lib xs)
    lib = ddGetObj(laLib)
    unless(lib
      lib = ddCreateLib(laLib strcat("./" laLib))
      techBindTechFile(lib "gpdk090")
      printf("LA_LIB created %s\n" laLib))
    printf("LA_LIB %s path=%s tech=%L\n" laLib lib~>readPath techGetTechLibName(lib))

    ;; INV_X1  A Y : n VSS|A|Y  p VDD|A|Y
    laCell("INV_X1" list("c" 0.12 "c") list("c" 0.24 "c")
      list(list(1 "A"))
      list(list("v" 0 laYN laYVSS) list("v" 0 laYP laYVDD) list("v" 2 laYN laYP))
      list(list("Y" 2)))

    ;; NAND2_X1  n VSS|B|n1|A|Y   p VDD|B|Y|A|VDD
    laCell("NAND2_X1" list("c" 0.24 "n" 0.24 "c") list("c" 0.24 "c" 0.24 "c")
      list(list(1 "B") list(3 "A"))
      list(list("v" 0 laYN laYVSS) list("v" 0 laYP laYVDD) list("v" 4 laYP laYVDD)
           list("v" 2 laYP laYTp) list("h" 2 4 laYTp) list("v" 4 laYTp laYN))
      list(list("Y" 4)))

    ;; NOR2_X1  n VSS|A|Y|B|VSS   p VDD|A|p1|B|Y
    laCell("NOR2_X1" list("c" 0.12 "c" 0.12 "c") list("c" 0.48 "n" 0.48 "c")
      list(list(1 "A") list(3 "B"))
      list(list("v" 0 laYN laYVSS) list("v" 4 laYN laYVSS) list("v" 0 laYP laYVDD)
           list("v" 2 laYN laYTn) list("h" 2 4 laYTn) list("v" 4 laYTn laYP))
      list(list("Y" 4)))

    ;; AOI21_X1  n VSS|B|Y|A1|n1|A2|VSS   p Y|B|p1|A1|VDD|A2|p1
    laCell("AOI21_X1" list("c" 0.12 "c" 0.24 "n" 0.24 "c") list("c" 0.48 "c" 0.48 "c" 0.48 "c")
      list(list(1 "B") list(3 "A1") list(5 "A2"))
      list(list("v" 0 laYN laYVSS) list("v" 6 laYN laYVSS) list("v" 4 laYP laYVDD)
           list("v" 2 laYP laYTp) list("h" 2 6 laYTp) list("v" 6 laYP laYTp)
           list("v" 2 laYN laYTn) list("h" 0 2 laYTn) list("v" 0 laYTn laYP))
      list(list("Y" 0)))

    ;; OAI21_X1  n VSS|B|n1|A1|Y|A2|n1 (n1 joined on Metal2)   p Y|B|VDD|A1|p1|A2|Y
    laCell("OAI21_X1" list("c" 0.24 "c" 0.24 "c" 0.24 "c") list("c" 0.24 "c" 0.48 "n" 0.48 "c")
      list(list(1 "B") list(3 "A1") list(5 "A2"))
      list(list("v" 0 laYN laYVSS) list("v" 2 laYP laYVDD)
           list("v" 4 laYN laYTp) list("h" 0 6 laYTp) list("v" 0 laYTp laYP) list("v" 6 laYTp laYP)
           list("pad" 2 laYN) list("pad" 6 laYN) list("via" laX(2) laYN) list("via" laX(6) laYN)
           list("m2" laX(2) - 0.13 laX(6) + 0.13 laYN))
      list(list("Y" 4)))

    ;; BLK_P = AOI21(A1=PI A2=GK B=GI Y=GON) + NAND2(A=PI B=PK Y=PON); PI joined on Metal2
    xs = laG * 8
    laHier("BLK_P" list(list("XG" "AOI21_X1" 0.0) list("XP" "NAND2_X1" xs))
      list(list("GI" "input" 0.0 1) list("PI" "input" 0.0 3) list("GK" "input" 0.0 5)
           list("PK" "input" xs 1) list("GON" "output" 0.0 0) list("PON" "output" xs 4))
      list(list("via" laX(3) laYIn) list("via" xs + laX(3) laYIn)
           list("m2" laX(3) - 0.13 xs + laX(3) + 0.13 laYIn)))

    ;; BLK_N = OAI21(A1=PIN A2=GKN B=GIN Y=GO) + NOR2(A=PIN B=PKN Y=PO); PIN joined on Metal2
    laHier("BLK_N" list(list("XG" "OAI21_X1" 0.0) list("XP" "NOR2_X1" xs))
      list(list("GIN" "input" 0.0 1) list("PIN" "input" 0.0 3) list("GKN" "input" 0.0 5)
           list("PKN" "input" xs 3) list("GO" "output" 0.0 4) list("PO" "output" xs 4))
      list(list("via" laX(3) laYIn) list("via" xs + laX(1) laYIn)
           list("m2" laX(3) - 0.13 xs + laX(1) + 0.13 laYIn)))

    laHier("GRY_P" list(list("XG" "AOI21_X1" 0.0))
      list(list("GI" "input" 0.0 1) list("PI" "input" 0.0 3) list("GK" "input" 0.0 5)
           list("GON" "output" 0.0 0))
      nil)

    laHier("GRY_N" list(list("XG" "OAI21_X1" 0.0))
      list(list("GIN" "input" 0.0 1) list("PIN" "input" 0.0 3) list("GKN" "input" 0.0 5)
           list("GO" "output" 0.0 4))
      nil)
    t))

unless(errset(laMain() t)
  printf("LA_ERROR SKILL error, see message above\n")
  laErr = laErr + 1)
printf("LA_SUMMARY errors=%d\n" laErr)
exit(if(laErr == 0 0 1))
