;; layout/pnr/dump_layout.il -- ghi hinh hoc cac cell la (Metal1..3, Via1..2, pin, bien) ra text
;; de layout/pnr/make_lef.py sinh LEF cho Encounter. Chay trong VM (layout/pnr/run_pnr.sh dump).
;;   DUMP_OUT=<file> virtuoso -nograph -restore layout/pnr/dump_layout.il
;; Dong ra: CELL lib name x1 y1 x2 y2 | RECT layer purpose x1 y1 x2 y2 | PIN name layer x1 y1 x2 y2 | END
dlErr = 0
procedure(dlCell(p lib cell)
  let((cv b)
    cv = dbOpenCellViewByType(lib cell "layout" "maskLayout" "r")
    if(!cv then printf("DL_ERROR khong mo duoc %s/%s\n" lib cell) dlErr = dlErr + 1
    else
      b = cv~>bBox
      fprintf(p "CELL %s %s %g %g %g %g\n" lib cell caar(b) cadar(b) caadr(b) cadadr(b))
      fprintf(p "NINST %d\n" length(cv~>instances))   ; >0: hinh cua instance con khong duoc ghi
      foreach(s cv~>shapes
        when(s~>objType == "rect" && member(s~>layerName list("Metal1" "Metal2" "Metal3" "Via1" "Via2" "prBoundary"))
          b = s~>bBox
          if(s~>pin then
            fprintf(p "PIN %s %s %g %g %g %g\n" s~>pin~>term~>name s~>layerName caar(b) cadar(b) caadr(b) cadadr(b))
          else
            fprintf(p "RECT %s %s %g %g %g %g\n" s~>layerName s~>purpose caar(b) cadar(b) caadr(b) cadadr(b)))))
      fprintf(p "END\n")
      dbClose(cv))))
procedure(dlMain()
  let((p)
    p = outfile(getShellEnvVar("DUMP_OUT"))
    foreach(lc list(
        '("ALU_CELLS_A" "INV_X1") '("ALU_CELLS_A" "NAND2_X1") '("ALU_CELLS_A" "NOR2_X1")
        '("ALU_CELLS_A" "AOI21_X1") '("ALU_CELLS_A" "OAI21_X1") '("ALU_CELLS_A" "BLK_P")
        '("ALU_CELLS_A" "BLK_N") '("ALU_CELLS_A" "GRY_P") '("ALU_CELLS_A" "GRY_N")
        '("ALU_STUB_B" "XOR2_X1") '("ALU_STUB_B" "XNOR2_X1") '("ALU_CELLS_B" "BOOTH_ENC")
        '("ALU_CELLS_B" "BOOTH_SEL") '("ALU_CELLS_B" "CMP42") '("ALU_CELLS_C" "FA_X1")
        '("ALU_CELLS_C" "HA_X1") '("ALU_CELLS_C" "INV_X4") '("ALU_CELLS_D" "CAS_X1")
        '("ALU_CELLS_P" "FILL1") '("ALU_CELLS_P" "FILL2") '("ALU_CELLS_P" "FILL4")
        '("ALU_CELLS_P" "FILL8") '("ALU_CELLS_P" "TIE0") '("ALU_CELLS_P" "TIE1"))
      dlCell(p car(lc) cadr(lc)))
    close(p)
    t))
unless(errset(dlMain() t) printf("DL_ERROR SKILL error\n") dlErr = dlErr + 1)
printf("DL_SUMMARY errors=%d\n" dlErr)
exit(if(dlErr == 0 0 1))
