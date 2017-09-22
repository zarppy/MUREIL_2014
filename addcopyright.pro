pro addcopyright

spawn,'ls *.py */*.py */*/*.py',files

nfiles = n_elements(files)

for icount = 0,nfiles -1 do BEGIN

    spawn,'head -3 '+files(icount),results

    print,files(icount)
    print, results

    if n_elements(results) gt 2 then BEGIN

        ; check and see if the license is already there
        ; if not, then cat the license on the start 
        if results(2) ne '# Copyright (C) University of Melbourne 2012' then BEGIN
            ; add on the copyright statement to the start of the file
            spawn,'cat copyright.txt '+files(icount)+' > tmp'
            print,'Replacing file with copyright version'
            spawn,'mv tmp '+files(icount)
        endif
    endif
    if n_elements(results) lt 3 then BEGIN
        spawn,'cat copyright.txt '+files(icount)+' > tmp'
        print,'Replacing file with copyright version'
        spawn,'mv tmp '+files(icount)
    endif

endfor

end
