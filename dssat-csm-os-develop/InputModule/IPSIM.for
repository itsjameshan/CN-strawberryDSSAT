C=======================================================================
C  IPSIM, Subroutine
C
C  Reads parameters related to field operation from FILEX file
C-----------------------------------------------------------------------
C  Revision history
C  01/01/1990 JWJ Written
C  05/28/1993 PWW Header revision and minor changes            
C  11/19/2003 CHP Added check for MEPHO and incompatible models.
C  02/21/2006 GH  Removed crop model selection
!  10/25/2006 CHP CRMODEL from FILEX overrides MODEL in DSSATPRO 
!  04/28/2008 CHP Added switch for CO2 from file (ICO2)
!  12/09/2009 CHP IPSIM separate file.  
!  02/11/2010 CHP Added checks for P model linked with crop models.
!  05/07/2020 FO  Added new Y4K subroutine call to convert YRDOY
!  05/07/2020 FO  Added check for SimLevel to set YRSIM using YRPLT
!  93/22/2022 GH Fix forecast issue
!  07/30/2023 FO  Initialized ATMOW and ATTP.
!  02/07/2025 CHP Move all codes checking after the call to External_SimControls
!                 so that we can do this once in the code instead of twice.
C-----------------------------------------------------------------------
C  INPUT  : LUNEXP,FILEX,LNSIM
C
C  LOCAL  : LN
C
C  OUTPUT : NYRS,NREPSQ,ISWWAT,ISWNIT,ISWSYM,ISWPHO,ISWPOT,ISWDIS,MEWTH,
C           MESIC,MELI,MEEVP,MEINF,MEPHO,ISIMI,ISIM,IPLTI,IIRRI,IFERI,
C           IRESI,IHARI,IOX,IDETO,IDETS,IDETG,IDETC,IDETW,IDETN,IDETP,IDETD,
C           PWDINF,PWDINL,SWPLTL,SWPLTH,SWPLTD,PTX,PTTN,DSOILX,THETACX,
C           IEPTX,IOFFX,IAMEX,DSOILN,SOILNC,SOILNX,NEND,RIP,NRESDL,
C           DRESMG,HDLAY,HLATE
!           MESOM, METMP, MESOL, MESEV, MEGHG
C-----------------------------------------------------------------------
C  Called : IPEXP
C
C  Calls  : ERROR IGNORE FIND YR_DOY
C-----------------------------------------------------------------------
C                         DEFINITIONS
C
C  HDLAY  :
C=======================================================================

      SUBROUTINE IPSIM (LUNEXP,LNSIM,SimLevel,TITSIM,NYRS,RUN,NREPSQ,
     & ISIMI,PWDINF,PWDINL,SWPLTL,NCODE,SWPLTH,SWPLTD,YEAR,
     & PTX,PTTN,DSOIL,THETAC,IEPT,IOFF,IAME,DSOILN,SOILNC,YRSIM,
     & SOILNX,NEND,RIP,NRESDL,DRESMG,HDLAY,HLATE,HPP,HRP,FTYPEN,
     & RSEED1,LINEXP,AIRAMT,EFFIRR,CROP,FROP,MODEL,RNMODE,FILEX,
     & CONTROL,ISWITCH,UseSimCtr,FILECTL,MODELARG,YRPLT)

      USE ModuleDefs
      USE ModuleData
      USE CsvOutput
      IMPLICIT NONE
      EXTERNAL ERROR, FIND, IGNORE, UPCASE, WARNING, IGNORE2, Y4K_DOY, 
     &  YR_DOY, MODEL_NAME, FILL_ISWITCH, External_SimControls, 
     &  GET_CROPD
      SAVE

      INCLUDE 'COMSWI.blk'

      CHARACTER*1   UPCASE,ISIMI, RNMODE
      CHARACTER*2   CROP
      CHARACTER*5   NEND,NCODE,IOFF,IAME, TEXT
      CHARACTER*6   ERRKEY,FINDCH
      CHARACTER*8   MODEL, MODELARG, CRMODEL, TRY_MODEL, Try_MODELARG
      CHARACTER*8   CTRMODEL
      CHARACTER*12  FILEX
      CHARACTER*16  CROPD
      CHARACTER*25  TITSIM
      CHARACTER*78  MSG(7)
      CHARACTER*120 FILECTL
      CHARACTER*128 CHARTEST

      INTEGER LNSIM,LUNEXP,ISECT,LINEXP,ISIM,NYRS,NREPSQ,FROP
      INTEGER PLDATE,PWDINF,PWDINL,HLATE,HDLAY,NRESDL
      INTEGER IFIND,LN,ERRNUM,FTYPEN,YRSIM,YEAR,RUN,RSEED1,RRSEED1
      INTEGER YRPLT
!     INTEGER FIST1, FIST2

      REAL DSOIL,THETAC,DSOILN,SOILNC,SOILNX,SWPLTL,SWPLTH,SWPLTD
      REAL PTX,PTTN,DRESMG,RIP,IEPT,HPP,HRP,AIRAMT,EFFIRR, AVWAT
!     REAL LDIFF, PREV_LINEXP
!     Vectors to save growth stage based irrigation
      REAL V_AVWAT(20)    
      REAL V_IMDEP(20)
      REAL V_ITHRL(20)
      REAL V_ITHRU(20), IFREQ
      INTEGER V_IRON(20), V_IFREQ(20)
      CHARACTER*5 V_IRONC(20)
      CHARACTER*5 V_IMETH(20)
      REAL V_IRAMT(20)
      REAL V_IREFF(20)
      INTEGER GSIRRIG, I, STAT, CHARLEN

      LOGICAL UseSimCtr, MulchWarn, SimLevel


!     2020-11-04 CHP Added for yield forecast mode, RNMODE = 'Y'
      INTEGER ENDAT, SeasDur, FODAT, FStartYear, FEndYear
      CHARACTER*15 FWFILE

      TYPE (SwitchType)  ISWITCH
      TYPE (ControlType) CONTROL

      PARAMETER (ERRKEY='IPSIM ')
                 FINDCH='*SIMUL'
                 
      DATA MulchWarn /.FALSE./

      !FO - IF SimLevel is not present set defaults
      IF (LNSIM .EQ. 0 .OR. .NOT. SimLevel) THEN
         LNSIM   = 0
         NYRS    = 1
         NREPSQ  = 1
         ISIMI   = 'S'
         !FO - YRPLT was already read and can be updated.
         YRSIM   = YRPLT
         RSEED1  = 2150
         ISWWAT  = 'Y'
         ISWNIT  = 'Y'
         ISWSYM  = 'Y'
         ISWPHO  = 'N'
         ISWPOT  = 'N'
         ISWDIS  = 'N'
         ISWCHE  = 'N'
         ISWTIL  = 'Y'

         IF (INDEX('FNQS',RNMODE) > 0) THEN
           ICO2 = 'D' !Default CO2 from CO2???.WDA file
         ELSE
           ICO2 = 'M' !Measured CO2 from CO2???.WDA file
         ENDIF

         MEWTH   = 'M'
         MESIC   = 'M'
         MELI    = 'E'
         MEEVP   = 'R'
         MEINF   = 'S'
         MEPHO   = 'L'
         MEHYD   = 'R'
         NSWITCH =  1
         MESOM   = 'G'
         MESOL   = '2'    !was '1'
         MESEV   = 'R'    !old Ritchie two-stage method
         METMP   = 'D'    !DSSAT / Kimball improved soil temperature
!        METMP   = 'E'    ! EPIC soil temp routine.
         MEGHG   = '0'
!                   0  => DSSAT original denitrification routine
!                   1  => DayCent N2O calculation

         IPLTI   = 'R'
         IIRRI   = 'R'
         IFERI   = 'R'
         IRESI   = 'R'
         IHARI   = 'M'
         IOX     = 'N'
         FROP    =  3
         IDETO   = 'Y'
         IDETS   = 'Y'
         IDETG   = 'Y'
         IDETN   = 'N'
         IDETC   = 'N'
         IDETW   = 'N'
         IDETP   = 'N'
         IDETD   = 'N'
         IDETL   = 'N'
         IDETH   = 'N'
         IDETR   = 'Y'
         EFFIRR  = 1.00
         AVWAT  = -99.
         THETAC  = 75.0
         IEPT    = 100.0
         DSOIL   = 30.0
         DSOILN  = 30.0
         AIRAMT  = 10.0
         IOFF    = 'GS000'
         IAME    = 'IR001'
         CRMODEL = '        '
         NCODE = "-99  "
         NEND  = "-99  "
       ELSE

!     ==============================================================
!     Read first line of simulation controls - GENERAL
 40      CALL FIND (LUNEXP,FINDCH,LINEXP,IFIND)
         IF (IFIND .EQ. 0) CALL ERROR (ERRKEY,1,FILEX,LINEXP)
 50      CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
         IF (ISECT .EQ. 1) THEN
            READ (CHARTEST,55,IOSTAT=ERRNUM) LN
            IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)
            IF (LN .NE. LNSIM) GO TO 50
            READ (CHARTEST,55,IOSTAT=ERRNUM) LN,NYRS,NREPSQ,ISIMI,
     &            YRSIM,RRSEED1,TITSIM,CRMODEL
            IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)
            IF (INDEX('G',RNMODE) .GT. 0) NYRS = 1
            IF ((RNMODE .NE. 'Q') .OR. (RNMODE .EQ. 'Q'
     &       .AND. RUN .EQ. 1)) THEN
               RSEED1 = RRSEED1
               IF (RSEED1 .LE. 0) THEN
                 RSEED1 = 2150
               ENDIF
            ENDIF
C  FO - 05/07/2020 Add new Y4K subroutine call to convert YRDOY
            !CALL Y2K_DOY (YRSIM)
            CALL Y4K_DOY (YRSIM,FILEX,LINEXP,ERRKEY,8)
            !Call Error before first weather day (RANGELH(1))
            CALL YR_DOY (YRSIM,YEAR,ISIM)
          ELSE
            BACKSPACE (LUNEXP)
            GO TO 40
         ENDIF
C
!     ==============================================================
C        Read SECOND line of simulation control - OPTIONS
C
         CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
         READ (CHARTEST,60,IOSTAT=ERRNUM) LN,ISWWAT,ISWNIT,ISWSYM,
     &        ISWPHO,ISWPOT,ISWDIS,ISWCHE,ISWTIL, ICO2
         IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)

         ISWWAT = UPCASE(ISWWAT)
         ISWNIT = UPCASE(ISWNIT)
         ISWSYM = UPCASE(ISWSYM)
         ISWPHO = UPCASE(ISWPHO)
         ISWPOT = UPCASE(ISWPOT)
         ISWDIS = UPCASE(ISWDIS)
         ISWCHE = UPCASE(ISWCHE)
         ISWTIL = UPCASE(ISWTIL)
         ICO2   = UPCASE(ICO2)

!     ==============================================================
C        Read THIRD line of simulation control - METHODS
C
         CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
         READ (CHARTEST,61,IOSTAT=ERRNUM) LN,MEWTH,MESIC,
     &        MELI,MEEVP,MEINF,MEPHO,MEHYD,NSWITCH, 
     &        MESOM, MESEV, MESOL, METMP, MEGHG
         !IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)
         MEWTH = UPCASE(MEWTH)
         MESIC = UPCASE(MESIC)
         MELI  = UPCASE(MELI)
         MEEVP = UPCASE(MEEVP)
         MEINF = UPCASE(MEINF)
         MEPHO = UPCASE(MEPHO)
         MESOM = UPCASE(MESOM)
         MEHYD = UPCASE(MEHYD)
         MESEV = UPCASE(MESEV)
         METMP = UPCASE(METMP)
         MEGHG = UPCASE(MEGHG)

!     ==============================================================
C        Read FOURTH line of simulation control - MANAGEMENT
C
         CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
         READ (CHARTEST,60,IOSTAT=ERRNUM) LN,IPLTI,IIRRI,
     &        IFERI,IRESI,IHARI
         IF (ERRNUM .NE. 0) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
         IPLTI = UPCASE(IPLTI)
         IIRRI = UPCASE(IIRRI)
         IFERI = UPCASE(IFERI)
         IRESI = UPCASE(IRESI)
         IHARI = UPCASE(IHARI)

!     ==============================================================
C        Read FIFTH line of simulation control - OUTPUTS
C
         CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
         IF (INDEX('FQ',RNMODE) < 1 .OR. RUN == 1) THEN
            READ (CHARTEST,65,IOSTAT=ERRNUM) LN,IOX,IDETO,
     &      IDETS,FROP,IDETG,IDETC,IDETW,IDETN,IDETP,IDETD,
     &      IDETL,IDETH,IDETR,
     &      FMOPT   ! VSH
            IF (ERRNUM .NE. 0) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
            IOX   = UPCASE(IOX)
            IDETO = UPCASE(IDETO)
            IDETS = UPCASE(IDETS)
            IDETG = UPCASE(IDETG)
            IDETC = UPCASE(IDETC)
            IDETW = UPCASE(IDETW)
            IDETN = UPCASE(IDETN)
            IDETP = UPCASE(IDETP)
            IDETD = UPCASE(IDETD)
            FMOPT = UPCASE(FMOPT)   ! VSH
          ENDIF

!     ==============================================================
C        Read SIXTH line of simulation control - AUTOMATIC PLANTING
C
         CALL IGNORE (LUNEXP,LINEXP,ISECT,CHARTEST)
         IF (ISECT .EQ. 1) THEN
            READ (CHARTEST,66,IOSTAT=ERRNUM) LN,PWDINF,PWDINL,
     &           SWPLTL,SWPLTH,SWPLTD,PTX,PTTN
            IF (ERRNUM .NE. 0) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
!            IF (PWDINF .LT. 1000) PWDINF = YEAR * 1000 + PWDINF
!            IF (PWDINL .LT. 1000) PWDINL = YEAR * 1000 + PWDINL
            
!     ==============================================================
C           Read SEVENTH line of simulation control - AUTOMATIC IRRIGATION
C
           DO I=1,20
                V_IMDEP (I) = -99 
                V_ITHRL (I) = -99
                V_ITHRU (I) = -99
                V_IRON  (I) = -99
!                V_IMETH (I) = -99
                V_IRAMT (I) = -99
                V_IREFF (I) = -99
                V_AVWAT (I) = -99
           END DO

           GSIRRIG = 1         ! Start Growth Stage index

           CALL IGNORE (LUNEXP,LINEXP,ISECT,CHARTEST)

           DO WHILE(ISECT .NE. 3)
 
               READ (CHARTEST,69,IOSTAT=ERRNUM) LN,DSOIL,THETAC,
     &               IEPT,IOFF,IAME,AIRAMT,EFFIRR,AVWAT, IFREQ
               IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)

!              Read value of AVWAT in text to check if blank or missing
               READ(CHARTEST,'(57x,A5)') TEXT     
               CHARLEN = LEN_TRIM(TEXT)
!              If TXAVWAT blank or missing set AVWAT -99 (for compatability with old files)
               IF (CHARLEN==0) AVWAT = -99.       

!              Read value of IFREQ in text to check if blank or missing
               READ(CHARTEST,'(63x,A5)') TEXT     
               CHARLEN = LEN_TRIM(TEXT)
!              If TXFREQ blank or missing set IFREQ = 0 (for compatability with old files)
               IF (CHARLEN==0) IFREQ = 0.0        

!             Save growth stage specific variables in data vectors
              V_IMDEP(GSIRRIG) = DSOIL                   
              V_ITHRL(GSIRRIG) = THETAC
              V_ITHRU(GSIRRIG) = IEPT
              READ(IOFF(4:5), *, IOSTAT = STAT) V_IRON (GSIRRIG)
              V_IRONC(GSIRRIG) = IOFF
              V_IMETH(GSIRRIG) = IAME
              V_IRAMT(GSIRRIG) = AIRAMT
              V_IREFF(GSIRRIG) = EFFIRR
              V_IFREQ(GSIRRIG) = NINT(IFREQ)
              V_AVWAT(GSIRRIG) = AVWAT

!             Read next line until a second tier header is found
              CALL IGNORE2(LUNEXP,LINEXP,ISECT,CHARTEST)                

              IF(ISECT .NE. 3) THEN
!                 Increase the counter by 1
                  GSIRRIG = GSIRRIG + 1                                 
              END IF
           END DO
           
!          Save value of first line as default for compatibility with old files
           DSOIL  = V_IMDEP(1)                         
           THETAC = V_ITHRL(1)
           IEPT   = V_ITHRU(1)
           IOFF   = V_IRONC(1)
           IAME   = V_IMETH(1)
           AIRAMT = V_IRAMT(1)
           EFFIRR = V_IREFF(1)
           AVWAT  = V_AVWAT(1)
           IFREQ  = FLOAT(V_IFREQ(1))

           SAVE_data % MGMT % V_IMDEP = V_IMDEP
           SAVE_data % MGMT % V_ITHRL = V_ITHRL
           SAVE_data % MGMT % V_ITHRU = V_ITHRU
           SAVE_data % MGMT % V_IRONC = V_IRONC
           SAVE_data % MGMT % V_IRON  = V_IRON
           SAVE_data % MGMT % V_IRAMT = V_IRAMT
           SAVE_data % MGMT % V_IREFF = V_IREFF
           SAVE_data % MGMT % V_AVWAT = V_AVWAT
           SAVE_data % MGMT % V_IFREQ = V_IFREQ
           SAVE_data % MGMT % GSIRRIG = GSIRRIG

C
!     ==============================================================
C           Read EIGHTH line of simulation control - AUTOMATIC N APPLICTION (not currently used)

C
            CALL IGNORE (LUNEXP,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,67,IOSTAT=ERRNUM) LN,DSOILN,SOILNC,
     &           SOILNX,NCODE,NEND
            IF (ERRNUM .NE. 0) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
            READ (NCODE,70,IOSTAT=ERRNUM) FTYPEN

C
!     ==============================================================
C           Read NINTH line of simulation control - AUTOMATIC RESIDUE APPLICAITON (not currently used)
C
            CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,68,IOSTAT=ERRNUM) LN,RIP,NRESDL,DRESMG
            IF (ERRNUM .NE. 0) CALL ERROR(ERRKEY,ERRNUM,FILEX,LINEXP)
C
!     ==============================================================
C           Read TENTH line of simulation control - AUTOMATIC HARVEST
C
            CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
          
C           Added AutoMow variables: HMFRQ, HMGDD, HMCUT, HMMOW, HRSPL, HMVS
            READ (CHARTEST,71,IOSTAT=ERRNUM) LN,HDLAY,HLATE,
     &           HPP,HRP,ISWITCH%HMFRQ,ISWITCH%HMGDD,ISWITCH%HMCUT,
     &           ISWITCH%HMMOW, ISWITCH%HRSPL, ISWITCH%HMVS
            IF (ERRNUM .NE. 0) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
            
!     ==============================================================
!           Read ELEVENTH line of simulation control - SIMULATION DATES
!           2020-11-04 CHP added forecast mode inputs
!           Also additional inputs to be implemented later

!     ENDAT = End of simulation date - for future use
!     SDUR  = Maximum duration of one season - for future use
!     FODAT = Forecast start date, i.e., day after last weather data available
!     FSTART= Ensemble start year - for future use
!     FEND  = Ensemble end year -for future use
!     FWFILE= Forecast weather file (for short term forecast) - for future use
!     FONAME= Forecast level name

            ENDAT = -99
            SeasDur = -99
            FODAT = -99
            FStartYear = -99
            FEndYear = -99
            FWFILE = "-99"

            CALL IGNORE(LUNEXP,LINEXP,ISECT,CHARTEST)
!            READ (CHARTEST,'(I3,9X,5I8,1X,A15)',IOSTAT=ERRNUM) 
!     &        LN, ENDAT, SeasDur, FODAT, FStartYear, FEndYear, FWFILE
            READ (CHARTEST,'(I3,25X,I8)',IOSTAT=ERRNUM) LN, FODAT

! CHP 2021-03-29 Allow  11th line of simcontrols to be missing.
! In this case, FODAT will be set equal to either last date in weather file or YRSIM.
            IF (ERRNUM .NE. 0 .OR. LN .NE. LNSIM
     &       .OR. ISECT .EQ. 0) THEN
! GH 03/2022 Fix issue with no blank lines at the end of FileX
              FODAT = -99
            ENDIF

!            IF (ERRNUM .NE. 0 .AND. RNMODE .EQ. 'Y') THEN
!              MSG(1) = 
!     &          "Error in forecast data, check simulation controls."
!              WRITE(MSG(2),'("End simulation date = ",I8)') ENDAT
!              WRITE(MSG(3),'("Maximum season duration = ",I8)') SeasDur
!              WRITE(MSG(4),'("Simulated forecast start date=",I8)')FODAT
!              WRITE(MSG(5),'("Forecast start year = ",I8)') FStartYear
!              WRITE(MSG(6),'("Forecast end year = ",I8)') FEndYear
!              WRITE(MSG(7),'("Short term forecast weather file = ",A5)')
!     &          FWFILE
!              CALL WARNING(7, ERRKEY, MSG)
!            ENDIF
            CONTROL % FODAT = FODAT
            
!     ==============================================================
C  FO - 05/07/2020 Add new Y4K subroutine call to convert YRDOY
            !CALL Y2K_DOY (HLATE)
!            IF(HLATE .LE. YRSIM) CALL ERROR (ERRKEY,ERRNUM,FILEX,LINEXP)
            IF(IHARI .EQ. 'A' .OR. IHARI .EQ. 'F') THEN
              CALL Y4K_DOY (HLATE,FILEX,LINEXP,ERRKEY,10)
            ELSE
              HLATE = -99
            ENDIF
            
            IF (HPP   .LT. 0.0)  HPP   = 100.
            IF (HRP   .LT. 0.0)  HRP   = 0.0
          ELSE
            PWDINF  =   1
            PWDINL  =   366
            SWPLTL  =   1.0
            SWPLTH  =   100.0
            SWPLTD  =   200.0
            PTX     =   50.0
            PTTN    =   1.0
            DSOIL   =   200.0
            THETAC  =   10.0
            IEPT    =   100.0
            IOFF    =   ' '
            HPP     =   100.0
            HRP     =     0.0
         ENDIF
      ENDIF

      REWIND (LUNEXP)

      CALL FILL_ISWITCH(
     &      CONTROL, ISWITCH, FROP, MODEL, NYRS, RNMODE)

!     Check Simulation control file for control overrides 
      CALL External_SimControls(
     &    CONTROL, FILECTL, ISWITCH,                      !Input
     &    UseSimCtr, CTRMODEL)                            !Output

      IF (UseSimCtr) THEN
        IOX     = ISWITCH % FNAME 
        ISIMI   = ISWITCH % ISIMI 
        ISWWAT  = ISWITCH % ISWWAT
        ISWNIT  = ISWITCH % ISWNIT
        ISWSYM  = ISWITCH % ISWSYM
        ISWPHO  = ISWITCH % ISWPHO
        ISWPOT  = ISWITCH % ISWPOT
        ISWDIS  = ISWITCH % ISWDIS
        ISWCHE  = ISWITCH % ISWCHE
        ISWTIL  = ISWITCH % ISWTIL
        ICO2    = ISWITCH % ICO2
        MEWTH   = ISWITCH % MEWTH 
        MESOM   = ISWITCH % MESOM 
        MELI    = ISWITCH % MELI  
        MEEVP   = ISWITCH % MEEVP 
        MEINF   = ISWITCH % MEINF 
        MEPHO   = ISWITCH % MEPHO 
        MEHYD   = ISWITCH % MEHYD 
        MESEV   = ISWITCH % MESEV 
        MESOL   = ISWITCH % MESOL 
        METMP   = ISWITCH % METMP 
        MEGHG   = ISWITCH % MEGHG 
        IPLTI   = ISWITCH % IPLTI 
        IIRRI   = ISWITCH % IIRRI 
        IFERI   = ISWITCH % IFERI 
        IRESI   = ISWITCH % IRESI 
        IHARI   = ISWITCH % IHARI 
        IDETO   = ISWITCH % IDETO 
        IDETS   = ISWITCH % IDETS 
        IDETG   = ISWITCH % IDETG 
        IDETC   = ISWITCH % IDETC 
        IDETW   = ISWITCH % IDETW 
        IDETN   = ISWITCH % IDETN 
        IDETP   = ISWITCH % IDETP 
        IDETD   = ISWITCH % IDETD 
        IDETL   = ISWITCH % IDETL 
        IDETH   = ISWITCH % IDETH 
        IDETR   = ISWITCH % IDETR 
        NSWITCH = ISWITCH % NSWI  
        FMOPT   = ISWITCH % FMOPT   ! VSH   
      
        NYRS  = CONTROL % NYRS  
        YRSIM = CONTROL % YRSIM 
        MODEL = CONTROL % MODEL 
!       MESIC = CONTROL % MESIC     
        FROP  = CONTROL % FROP
        
      ENDIF

!     =============================================================================
!     Check codes for valid values 
!     2025-02-07 CHP moved these here so that a single set of checks can be done for
!     both FileX values and those from the external simulation controls.
!     Previously, changes to checks in FileX were not also done for simulation controls.

C-----------------------------------------------------------------------
C    Select Model Name and Path -- order of priority:
!     CTRMODEL is value from control file override -- this is used
!         over all other values if valid. (Done in External_SimControls)
!     CRMODEL is read from FILEX.  Use this if no control file.  
!     MODELARG is from command line argument list. Third priority. 
!     Last, use value from DSSATPRO.vxx.
C-----------------------------------------------------------------------
!     -------------------------------------------------
!     Line 1
!     -------------------------------------------------
!     First check model from external simulation control file 
      TRY_MODEL = CTRMODEL  !from external control file
      CALL MODEL_NAME (CROP, DSSATP, TRY_MODEL, MODEL)

!     Next check model name from FILEX
!     If CTR file model name was not acceptable, then try the 
!       model name read from FileX.  
      IF (TRY_MODEL /= MODEL) THEN
        TRY_MODEL = CRMODEL   !from FileX
        CALL MODEL_NAME (CROP, DSSATP, TRY_MODEL, MODEL)

!       If FILEX model name was not acceptable, then try the 
!         model name read from command line.  If this is not OK, 
!         get MODEL name from DSSATPRO file
        IF (TRY_MODEL /= MODEL) THEN
!         Fallow must be associated with CRGRO model (for now)
          IF (CROP == 'FA') THEN
            Try_MODELARG(1:5) = "CRGRO"
          ELSE
            Try_MODELARG = MODELARG  !From command line
          ENDIF
          CALL MODEL_NAME (CROP, DSSATP, Try_MODELARG, MODEL)
        ENDIF
      ENDIF

!     Planting date needed for generic start of simulation
      SELECT CASE(IPLTI)
           CASE('R'); PLDATE = YRPLT
           CASE('A'); PLDATE = PWDINF
      END SELECT

!     Check for N fixation in CROPGRO crops
      SELECT CASE (CROP)
           CASE ('BN','SB','PN','PE','CH','PP','GY',
     &           'VB','CP','CB','FB','GB','LT','AL',
     &           'CV','BG')
!       Do nothing -- these crops fix N and can have Y or N
           CASE DEFAULT; ISWSYM ='N' !other crops don't have a choice
      END SELECT

      IF (ISWCHE .EQ. ' ') THEN
         ISWCHE = 'N'
      ENDIF

      IF (ISWTIL .EQ. ' ') THEN
         ISWTIL = 'N'
      ENDIF

      IF (ISWWAT .EQ. 'N') THEN
         ISWNIT = 'N'
         ISWPHO = 'N'
!        ISWCHE = 'N'
      ENDIF

      IF (INDEX('FNQS',RNMODE) > 0) THEN
!       For sequence, seasonal runs, default CO2 uses static value
        IF (INDEX ('WMD', ICO2) < 1) ICO2 = 'D'
      ELSE
!       For experimental runs, default CO2 uses measured values
        IF (INDEX ('WMD', ICO2) < 1) ICO2 = 'M'
      ENDIF

!     -------------------------------------------------
!     Line 3
!     -------------------------------------------------
      IF (MEPHO .EQ. 'L' .AND. MODEL(1:5) .NE. 'CRGRO' 
     &  .and. model(1:5) .ne. 'PRFRM' ) THEN
        MEPHO = 'C'
        WRITE(MSG(1),80)
        WRITE (MSG(2),81) MODEL(1:5)
        CALL WARNING(2, "IPEXP ", MSG)

   80 FORMAT('Photosynthesis method (PHOTO in FILEX) has been changed')
   81 FORMAT('from "L" to "C" for compatibility with crop model, '
     &            ,A5,'.') 
      ENDIF

      IF (INDEX('PG',MESOM) .EQ. 0) THEN
         MESOM = 'G'
      ENDIF
      
      IF (INDEX('G',MESOM)   > 0 .AND. 
     &    INDEX('FQ',RNMODE) > 0 .AND. 
     &    INDEX('N',MEINF)  == 0) THEN
        MEINF = 'N'
        IF (.NOT. MulchWarn) THEN
          MSG(1)=
     &  "Long-term simulation of surface residues may not be accurate"
             MSG(2)=
     &  "when using Godwin soil organic matter module.  The effects of"
             MSG(3)=
     &  "a surface mulch layer on runoff and evaporation will " //
     &       "not be modeled."  
             MSG(4)=
     &  "Simulation Options/Methods/Infiltration = 'No mulch effects'"
             MSG(5)=
     &  "You may want to consider using the Parton (CENTURY) method of"
             MSG(6)= "modeling soil organic matter."
             CALL WARNING(6,ERRKEY,MSG)
             MulchWarn = .TRUE.
        ENDIF
      ENDIF

!     ** DEFAULT MESOL = 2 ** 3/26/2007
!     MESOL = '1' Original soil layer distribution. Calls LYRSET.
!     MESOL = '2' New soil layer distribution. Calls LYRSET2.
!     MESOL = '3' User specified soil layer distribution. Calls LYRSET3.
      IF (INDEX('123',MESOL) < 1) THEN
         MESOL = '2'
      ENDIF

!     3/27/2016 chp Default soil temperature method is EPIC
!     7/21/2016 chp Default soil temperature method is DSSAT, per GH
!     5/04/2023  FO Default ST method is TMA(1) = TAVG (BK changes)
      IF (INDEX('EDR',METMP) < 1) METMP = 'D'
!      METMP = 'D' - default DSSAT (improved Kimball) soil temperature
!      METMP = 'R' - previous DSSAT default method (Ritchie)
!      METMP = 'E' - EPIC soil temperature routine

!     Default greenhouse gas method is DSSAT
      IF (INDEX('01',MEGHG) < 1) MEGHG = '0'

      SELECT CASE(MESEV)
         CASE('R','r'); MESEV = 'R'
         CASE('s','S'); MESEV = 'S'
         CASE DEFAULT;  MESEV = 'R'   !Default method Ritchie
      END SELECT

      IF (MEEVP == 'Z' .AND. MEPHO /= 'L') CALL ERROR(ERRKEY,3,' ',0)

      IF (MEHYD .EQ. ' ') MEHYD = 'R'

      IF (NSWITCH .LE. 0 .AND. ISWNIT .EQ. 'Y') THEN
        NSWITCH = 1
      ENDIF

!     ==============================================================
!     -------------------------------------------------
!     Line 4
!     -------------------------------------------------
C     TF, FO & DP - 2022-07-12 - AutomaticMOW Switch
!     2023-07-30 FO Initialized ATMOW and ATTP.
!     W - AutoMOW days frequency
!     X - AutoMOW GDD
!     Y - SmartMOW days frequency
!     Z - SmartMOW GDD
      ISWITCH%ATMOW = .FALSE.
      ISWITCH%ATTP = ' '
      IF(IHARI .EQ. 'W') THEN
        ISWITCH%ATMOW = .TRUE.
        ISWITCH%ATTP = 'W'
      ELSEIF(IHARI .EQ. 'X') THEN
        ISWITCH%ATMOW = .TRUE.
        ISWITCH%ATTP = 'X'
      ELSEIF(IHARI .EQ. 'Y') THEN
        ISWITCH%ATMOW = .TRUE.
        ISWITCH%ATTP = 'Y'
      ELSEIF(IHARI .EQ. 'Z') THEN
        ISWITCH%ATMOW = .TRUE.
        ISWITCH%ATTP = 'Z'
      ELSE
        ISWITCH%ATMOW = .FALSE.
      ENDIF

      IF ((INDEX('CSPT',CROP)) .GT. 0) THEN
        IF (IHARI .EQ. 'A') THEN
           WRITE(MSG(1),'("Automatic harvest option ",
     &       "is not valid for crop type: ",A2)') CROP
           CALL WARNING(1, ERRKEY, MSG)
           CALL ERROR (ERRKEY,4,FILEX,LINEXP)
        ENDIF
      ENDIF
       
      IF ((INDEX('CS',CROP)) .GT. 0) THEN
        IF (IHARI .EQ. 'M') THEN
          WRITE(MSG(1),'("Harvest at maturity option is ",
     &      "not valid for crop type: ",A2)') CROP
          CALL WARNING(1, ERRKEY, MSG)
          CALL ERROR ('IPSIM ',11,FILEX,LINEXP)
        ENDIF
      ENDIF

      IF ((INDEX('PT',CROP)) .GT. 0) THEN
        IF (IPLTI .EQ. 'A') THEN
           WRITE(MSG(1),'("Automatic planting option is ",
     & "not valid for crop type: ",A2)') CROP
           CALL WARNING(1, ERRKEY, MSG)
           CALL ERROR (ERRKEY,5,FILEX,LINEXP)
        ENDIF
      ENDIF

!     -------------------------------------------------
!     Line 5
!     -------------------------------------------------
!     FMOPT = 'A': ASCII format output
!     FMOPT = 'C': CSV format output
!     By default, use ASCII outputs
      IF (INDEX('CA',FMOPT) < 1) FMOPT = 'A'

!     IDETL = VBOSE
!       0  Only Summary.OUT
!       N  Minimal output  
!       Y  Normal output   
!       D  Detailed output 
!       A  All outputs     

      IF (IDETL .EQ. ' ') IDETL = 'N'
      IDETL = UPCASE(IDETL)
      IF (IDETH .EQ. ' ') IDETH = 'N'
      IDETH = UPCASE(IDETH)
      IF (IDETR .EQ. ' ') IDETR = 'Y'
      IDETR = UPCASE(IDETR)

!     Verbose output switch
      IF (IDETL == '0') THEN
!       VBOSE = zero, suppress all output except Summary and Evaluate
        IDETS = 'Y'
        IDETG = 'N' 
        IDETC = 'N' 
        IDETW = 'N' 
        IDETN = 'N' 
        IDETP = 'N' 
        IDETD = 'N' 
        IDETH = 'N' 
        IDETR = 'N' 
        IDETO = 'E'
!       Seasonal, Spatial, and Yield forecast runs do not get evaluate file when IDETL=0
        IF (INDEX('SNY',RNMODE) > 0) IDETO = 'N'
      ELSEIF (IDETL == 'A' .OR. IDETL == 'D') THEN
!       VBOSE = 'A', generate all output
        IDETS = 'A'
        IDETO = 'Y'
        IDETG = 'Y' 
        IDETC = 'Y' 
        IDETW = 'Y' 
        IDETN = 'Y' 
        IDETP = 'Y' 
        IDETD = 'Y' 
        IDETH = 'Y' 
        IDETR = 'Y' 
!       Set IDETL back to "D" so no need for changes elsewhere
!       IDETL = 'D' 
        FROP  = 1
      ENDIF

      IF (FROP .LE. 0) FROP = 10

!     -------------------------------------------------
!     Line 6
!     -------------------------------------------------
C  FO - 05/07/2020 Add new Y4K subroutine call to convert YRDOY
      !CALL Y2K_DOY (PWDINF)
      !CALL Y2K_DOY (PWDINL)
      IF(IPLTI .EQ. 'A' .OR. IPLTI .EQ. 'F') THEN
        CALL Y4K_DOY (PWDINF,FILEX,LINEXP,ERRKEY,9)
        CALL Y4K_DOY (PWDINL,FILEX,LINEXP,ERRKEY,9)
      ELSE
        PWDINF = -99
        PWDINL = -99
      ENDIF

      CALL FILL_ISWITCH(
     &      CONTROL, ISWITCH, FROP, MODEL, NYRS, RNMODE)

      CALL PUT(CONTROL)  
      CALL PUT(ISWITCH)

!     --------------------------------------------------------------------
!     Check for N model compatible with crop model
      IF (ISWNIT /= 'N') THEN
        SELECT CASE(MODEL(1:5))
        CASE ('SCCSP', 'SCSAM')
!           N model has NOT been linked for these models
!           Print a warning message.
            CALL GET_CROPD(CROP, CROPD)
            CROPD = ADJUSTL(CROPD)

            WRITE(MSG(1),
     &         '("Nitrogen dynamics model has not been developed for "
     &         ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
!            MSG(2)="Model will run if soils and species P data" //
!     &         " are supplied."
!            MSG(3)="User must verify validity of crop response."
            MSG(2)="Please contact the CSM development team if " // 
     &         "you wish to "
            WRITE(MSG(3),'("contribute to development of a N model for "
     &          ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
            MSG(4) = "N simulation will be switched off."
            CALL WARNING(4,ERRKEY,MSG)
            ISWNIT = 'N'
            ISWPHO = 'N'
            ISWPOT = 'N'
!           CALL ERROR('IPSIM', 6, "", 0)
        END SELECT
      ENDIF

!     --------------------------------------------------------------------
!     Check for phosphorus model compatible with crop model
!      IF (ISWPHO /= 'N') THEN
!       Check for validity of P model for this crop
!        SELECT CASE(MODEL(1:5))
        !CASE('CRGRO','MZCER','RICER')
        !  SELECT CASE(CONTROL % CROP)
        !  CASE('SB','FA','MZ','RI','PN') 
!           Phosphorus model has been enabled and tested for these crops, do nothing
         
! MA (19dec2013) to test P coupling to SG ceres 
       IF (ISWPHO /= 'N') THEN
        SELECT CASE(MODEL(1:5))
! chp 2019-08-19 remove rice from P model list
! RICER047.SPE file does not have P section.
!       CASE('CRGRO','MZCER','RICER','SGCER')
        CASE('CRGRO','MZCER','SGCER')
          SELECT CASE(CONTROL % CROP)
!         CASE('SB','FA','MZ','RI','PN','SG') 
!         CASE('SB','FA','MZ','PN','SG') 
          CASE('SB','FA','MZ','PN','SG','TM','GB') 
!           Phosphorus model has been enabled and tested for these crops, do nothing

          CASE DEFAULT
!           P model has NOT been tested for the remainder of the crops
!           Print a warning message.
            CALL GET_CROPD(CROP, CROPD)
            CROPD = ADJUSTL(CROPD)

            WRITE(MSG(1),
     &         '("Phosphorus model has not been tested for "
     &         ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
!            MSG(2)="Model will run if soils and species P data" //
!     &         " are supplied."
!            MSG(3)="User must verify validity of crop response."
            MSG(2)="Please contact the CSM development team if " // 
     &         "you wish to "
            WRITE(MSG(3),'("contribute to development of a P model for "
     &          ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
            CALL WARNING(3,ERRKEY,MSG)
            CALL ERROR('IPSIM', 6, "", 0)
          END SELECT

        CASE DEFAULT
!         Crop model has not been linked to P model.
!         Print a warning message. stop the run.
          WRITE(MSG(1),
     &       '("Phosphorus model has not been enabled for ",
     &       A5," model.")') MODEL(1:5)
          MSG(2)="Please contact the CSM development team if you " //
     &          "wish to contribute to "
          WRITE(MSG(3),'("development of a P model for ",A5,".")')
     &        MODEL(1:5)
          CALL WARNING(3,ERRKEY,MSG)
          CALL ERROR('IPSIM', 6, "", 0)
        END SELECT
      ENDIF

!     --------------------------------------------------------------------
!     Check for potassium model compatible with crop model
      IF (ISWPOT /= 'N') THEN
!       Check for validity of K model for this crop
        SELECT CASE(MODEL(1:5))
        CASE('MZCER','RICER')
!          SELECT CASE(CONTROL % CROP)
!          CASE('MZ','RI') 
!!           Potassium model has been enabled and tested for these crops, do nothing
!
!          CASE DEFAULT
!           K model has NOT been tested for the remainder of the CROPGRO crops
!           Print a warning message, but allow the user to continue.
            CALL GET_CROPD(CROP, CROPD)
            CROPD = ADJUSTL(CROPD)

            WRITE(MSG(1),
     &         '("Potassium model has not been tested for "
     &         ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
!            MSG(2)="Model will run if soils and species K data" //
!     &         " are supplied."
!            MSG(3)="User must verify validity of crop response."
            MSG(2)="Please contact the CSM development team if " // 
     &         "you wish to "
            WRITE(MSG(3),'("contribute to development of a K model for "
     &          ,A5,1X,A,".")') MODEL(1:5), TRIM(CROPD)
            CALL WARNING(3,ERRKEY,MSG)
            CALL ERROR('IPSIM', 7, "", 0)
!          END SELECT

        CASE DEFAULT
!         Crop model has not been linked to K model.
!         Print a warning message. stop the run.
          WRITE(MSG(1),
     &       '("Potassium model has not been enabled for ",
     &       A5," model.")') MODEL(1:5)
          MSG(2)="Please contact the CSM development team if you " //
     &          "wish to contribute to "
          WRITE(MSG(3),'("development of a K model for ",A5,".")')
     &        MODEL(1:5)
          CALL WARNING(3,ERRKEY,MSG)
          CALL ERROR('IPSIM', 7, "", 0)
        END SELECT
      ENDIF

      CALL FILL_ISWITCH(
     &      CONTROL, ISWITCH, FROP, MODEL, NYRS, RNMODE)

      RETURN

C-----------------------------------------------------------------------
C     FORMAT Strings
C-----------------------------------------------------------------------

  55  FORMAT (I3,11X,2(1X,I5),5X,A1,1X,I5,1X,I5,1X,A25,1X,A8)
  60  FORMAT (I3,11X,9(5X,A1))
  61  FORMAT (I3,11X,7(5X,A1),5X,I1,5(5X,A1))
  65  FORMAT (I3,11X,3(5X,A1),4X,I2,9(5X,A1),
     &5X, A1)   ! VSH
  66  FORMAT (I3,11X,2(1X,I5),5(1X,F5.0))
  67  FORMAT (I3,11X,3(1X,F5.0),2(1X,A5),1X,F5.0,1X,F5.0)
  68  FORMAT (I3,11X,1X,F5.0,1X,I5,1X,F5.0)
!69  FORMAT (I3,11X,3(1X,F5.0),2(1X,A5),1X,F5.0,1X,F5.0,1X,F5.0,1X,I5,
!    &        1X,I5,1x,F5.0, 2(1x, F5.3))
  69  FORMAT(I3,11X,3(1X,F5.0),2(1X,A5),1X,F5.0,1X,F5.0,1X,F5.0,1X,F6.0)
  70  FORMAT (3X,I2)
! FO/TF - New reading format for AutomaticMOW
  71  FORMAT (I3,11X,2(1X,I5),2(1X,F5.0),1X,I5,1X,I5,1X,F5.2,3(1X,I5))
      END SUBROUTINE IPSIM


!=======================================================================
!  FILL_ISWITCH, Subroutine
!
!  Copies values to ISWITCH variable, determines what values are carried
!     over in sequence runs.
!-----------------------------------------------------------------------
!  Revision history
!  10/26/2007 CHP Written
!-----------------------------------------------------------------------
!  Called : IPSIM
!  Calls  : none
!=======================================================================
      SUBROUTINE FILL_ISWITCH(
     &      CONTROL, ISWITCH, FROP, MODEL, NYRS, RNMODE)
      USE ModuleDefs 
      USE ModuleData
      USE CsvOutput   ! VSH
      INCLUDE 'COMSWI.blk'
      INCLUDE 'COMIBS.blk'

      CHARACTER*1 RNMODE
      CHARACTER*8 MODEL
      INTEGER FROP, NYRS
      
      TYPE (SwitchType) ISWITCH
      TYPE (ControlType)CONTROL

!     Skip some variables for sequenced runs -- need to keep values
!     from first run
      IF (INDEX('FQ',RNMODE) <= 0 .OR. CONTROL % RUN == 1) THEN
        ISWITCH % ISWWAT = ISWWAT  !water simulation
        ISWITCH % ISWNIT = ISWNIT  !N simulation
        ISWITCH % ISWPHO = ISWPHO  !P simulation
        ISWITCH % ISWPOT = ISWPOT  !K simulation
        ISWITCH % ISIMI  = ISIMI   !start of simulation switch
        ISWITCH % ICO2   = ICO2    !atmospheric CO2 data source
        ISWITCH % MEWTH  = MEWTH   !weather data source
        ISWITCH % MESOM  = MESOM   !SOM method
        ISWITCH % MEINF  = MEINF   !infiltration method (mulch effects)
        ISWITCH % MEHYD  = MEHYD   !hydrology
        ISWITCH % MESEV  = MESEV   !soil evaporation
        ISWITCH % MESOL  = MESOL   !soil layer distribution
        ISWITCH % METMP  = METMP   !soil temperature method
        ISWITCH % MEGHG  = MEGHG   !greenhouse gas calculations
        ISWITCH % IDETO  = IDETO   !overview file
        ISWITCH % IDETS  = IDETS   !summary file
        ISWITCH % IDETG  = IDETG   !growth output files
        ISWITCH % IDETC  = IDETC   !carbon output
        ISWITCH % IDETW  = IDETW   !water output
        ISWITCH % IDETN  = IDETN   !N output
        ISWITCH % IDETP  = IDETP   !P output
        ISWITCH % IDETD  = IDETD   !disease and pest output 
        ISWITCH % IDETL  = IDETL   !detail output (verbosity)
        ISWITCH % IDETH  = IDETH   !chemical output
        ISWITCH % IDETR  = IDETR   !management operations output
        ISWITCH % NSWI   = NSWITCH !N computations switch
        CONTROL % NYRS   = NYRS    !number of years simulated
        CONTROL % FROP   = FROP    !frequency of output

!       chp moved 12/9/2009
        ISWITCH % MEEVP  = MEEVP     !potential ET method
        ISWITCH % FNAME  = IOX       !output file name
!       VSH        
        ISWITCH % FMOPT  = FMOPT
      ENDIF
 
!     Use these values for all runs
      ISWITCH % ISWDIS = ISWDIS    !pests and disease
      ISWITCH % ISWCHE = ISWCHE    !chemical application
      ISWITCH % ISWTIL = ISWTIL    !tillage
      ISWITCH % MELI   = MELI      !light interception
      ISWITCH % IPLTI  = IPLTI     !planting switch
      ISWITCH % IIRRI  = IIRRI     !irrigation switch
      ISWITCH % IFERI  = IFERI     !fertilizer switch
      ISWITCH % IRESI  = IRESI     !residue addition switch
      ISWITCH % IHARI  = IHARI     !harvest switch
    
      CONTROL % YRSIM  = YRSIM     !simulation start date
      CONTROL % MODEL  = MODEL     !crop growth model
!     CONTROL % MESIC  = MESIC     !initial conditions (no longer used)

!     chp moved 12/9/2009
      ISWITCH % ISWSYM = ISWSYM    !symbiosis (N-fixation)
      ISWITCH % MEPHO  = MEPHO     !photsynthesis method

      CALL PUT(ISWITCH)
      CALL PUT(CONTROL)

      RETURN
      END SUBROUTINE FILL_ISWITCH
!=======================================================================


!=======================================================================
!  External_SimControls, Subroutine
!
!  Reads external simulation controls file. These values override the 
!     values in the FileX simulation controls.
!-----------------------------------------------------------------------
!  Revision history
!  06/29/2007 CHP Written
!-----------------------------------------------------------------------
!  Called : IPSIM
!
!  Calls  : ERROR IGNORE FIND YR_DOY
!=======================================================================

      SUBROUTINE External_SimControls(
     &    CONTROL, FILECTL, ISWITCH,                      !Input
     &    UseSimCtr, CTRMODEL)                            !Output

      USE ModuleDefs
      IMPLICIT NONE
      EXTERNAL ERROR, FIND, IGNORE, UPCASE, WARNING, IGNORE2, 
     &  Y4K_DOY, YR_DOY, MODEL_NAME, GETLUN, FIND_IN_FILE, LENSTRING, 
     &  CHECK_I, CHECK_A, INFO, MSG_TEXT
      SAVE

      CHARACTER*1 UPCASE,ISIMI, MEPHO_SAVE, ISWSYM_SAVE
      CHARACTER*1 ISWWAT,ISWNIT,ISWSYM,ISWPHO,ISWPOT,ISWDIS,MEWTH,MESIC
      CHARACTER*1 ICO2
      CHARACTER*1 MELI,MEEVP,MEINF,MEPHO,IPLTI,IIRRI,IFERI,IRESI,IHARI
      CHARACTER*1 ISWCHE,ISWTIL,MEHYD,MESOM, MESOL, MESEV, METMP, MEGHG
      CHARACTER*1 IDETO,IDETS,IDETG,IDETC,IDETW,IDETN,IDETP,IDETD,IOX
      CHARACTER*1 IDETH,IDETL, IDETR
      CHARACTER*1 FMOPT
      CHARACTER*1 NSWITCH_txt
      CHARACTER*3 FROP_txt
      CHARACTER*5 NYRS_txt, NREPSQ_txt, YRSIM_txt
      CHARACTER*6 ERRKEY,FINDCH, SECTION
      CHARACTER*8 MODEL, CTRMODEL
      CHARACTER*12 FILEX  !, DSSATS
      CHARACTER*78 MSG(50)
      CHARACTER*102 SIMCTR
      CHARACTER*120 INPUTX, FILECTL
      CHARACTER*128 CHARTEST

      INTEGER CTRNO, ERRNUM, FOUND, FROP, I, IFIND, IPX, ISECT, ISIM
      INTEGER LEVEL, LINEXP, NMSG, NREPSQ, NSWITCH, NYRS
      INTEGER RSEED1, SCLun, YEAR, YRSIM, YRSIM_ERR
      INTEGER SimLen, LenString, FIND_IN_FILE
      INTEGER YRSIM_SAVE

      TYPE (SwitchType)  ISWITCH
      TYPE (ControlType) CONTROL

      LOGICAL FIRST, FEXIST, UseSimCtr
      DATA FIRST /.TRUE./

      PARAMETER (ERRKEY = 'SIMCTR')

      MEPHO_SAVE  = ISWITCH % MEPHO
      ISWSYM_SAVE = ISWITCH % ISWSYM
      YRSIM_SAVE  = CONTROL % YRSIM
!-----------------------------------------------------------------------
      IF (FIRST) THEN
        FIRST = .FALSE.
        UseSimCtr = .FALSE.
        YRSIM_txt   = "  -99"

        IF (LEN(TRIM(FILECTL)) < 4 .OR. INDEX(FILECTL," ") < 4) RETURN

        I = INDEX(FILECTL,SLASH)
        IF (I < 1) THEN
!         No path provided -- look first in current directory
          INQUIRE (FILE = FILECTL, EXIST = FEXIST)
          IF (.NOT. FEXIST) THEN

!           Next look in DSSAT47 directory
            CALL GETARG (0,INPUTX)      !Name of model executable
            IPX = LEN_TRIM(INPUTX)

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Temporarily fix DSSATPRO file name for debugging purposes:
!     To use these Debug lines of code (letter D in column 1) with IVF:
!     1) Go to pull down menu Project -> Settings -> Fortran (Tab) ->
!       Debug (Category) -> Check box for Compile Debug(D) Lines
!     2)  Specify name of DSSATPRO file here:
!D     INPUTX = 'C:\DSSAT47\DSCSM048.EXE'
!D     IPX = 23
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            IF (IPX > 12) THEN
              DO I = IPX, 0, -1
                IF (INPUTX(I:I) .EQ. SLASH) EXIT
              END DO
              SIMCTR = INPUTX(1:I) // FILECTL
            ELSE
              RETURN
            ENDIF
          ELSE
            SIMCTR = FILECTL
          ENDIF
        ENDIF

        INQUIRE (FILE = SIMCTR, EXIST = FEXIST)
        IF (.NOT. FEXIST) THEN
          SIMCTR = TRIM(STDPATH) // TRIM(FILECTL)
        ENDIF

        INQUIRE (FILE = SIMCTR, EXIST = FEXIST)
        IF (.NOT. FEXIST) THEN
          MSG(1) = "Simulation controls file does not exist."
          MSG(2) = SIMCTR
          MSG(3) = "Use controls from experiment file."
          CALL WARNING(3,ERRKEY,MSG)
          RETURN
        ENDIF

        CALL GETLUN('SIMCNTL', SCLun)
        OPEN (UNIT = SCLun, FILE = SIMCTR, IOSTAT =ERRNUM)
        IF (ERRNUM /= 0) RETURN

        SECTION = '@CTRNO'
        FOUND = FIND_IN_FILE(SECTION,SCLun)
        IF (FOUND == 1) THEN
          CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
          IF (ISECT == 1) THEN
            READ(CHARTEST,"(I6)",IOSTAT=ERRNUM) CTRNO
          ELSE
            ERRNUM = 100
          ENDIF
          IF (ERRNUM > 0) THEN
            MSG(1) = "Error reading simulation control file."
            WRITE(MSG(2),'(A,A)') "File: ",SIMCTR(1:72)
            CALL WARNING(2, ERRKEY, MSG)
            RETURN
          ENDIF
          IF (CTRNO < 1) THEN
            MSG(1) = "External control file:"
            WRITE(MSG(2),'(A,A)') "  ", SIMCTR(1:76)
            WRITE(MSG(3),'(A,I6,A)') "Control level: ", CTRNO, 
     &        "    No external controls will be used."
            CALL WARNING(3, ERRKEY, MSG)
            RETURN
          ENDIF
        ELSE
          MSG(1) = "Error reading simulation control file."
          WRITE(MSG(2),'(A,A)') "File: ",SIMCTR(1:72)
          WRITE(MSG(3),'(A,A)') "Control section not found: ", SECTION
          CALL WARNING(3, ERRKEY, MSG)
          RETURN
        ENDIF

        CONTROL % SimControl = SIMCTR
        SimLen = LenString(CONTROL % SimControl)
        MSG(1) = "Simulation Controls override with file:"
        WRITE(MSG(2),'(A)') CONTROL % SimControl(1:SimLen)
        WRITE(MSG(3),'(A,I6)') "Control Level: ", CTRNO
        MSG(4)="The following switches and options will override values"
        MSG(5)="  found in the Experiment files, if appropriate:"
        NMSG = 5

!       Initialize override values
        NYRS    = CONTROL % NYRS
        NREPSQ  = 1
        ISIMI   = ' '
        RSEED1  = 2150

        ISWWAT  = ' '
        ISWNIT  = ' '
        NSWITCH = ISWITCH % NSWI
        ISWSYM  = ' '
        ISWPHO  = ' '
        ISWPOT  = ' '
        ISWDIS  = ' '
        ISWCHE  = ' '
        ISWTIL  = ' '

        ICO2    = ' '
        MEWTH   = ' '
        MESIC   = ' '
        MELI    = ' '
        MEEVP   = ' '
        MEINF   = ' '
        MEPHO   = ' '
        MEHYD   = ' '
        MESOM   = ' '
        METMP   = ' '
        MEGHG   = ' '
        MESOL   = ' '
        MESEV   = ' '
        IPLTI   = ' '
        IIRRI   = ' '
        IFERI   = ' '
        IRESI   = ' '
        IHARI   = ' '
        IOX     = ' '
        FROP    = CONTROL % FROP
        IDETO   = ' '
        IDETS   = ' '
        IDETG   = ' '
        IDETN   = ' '
        IDETC   = ' '
        IDETW   = ' '
        IDETP   = ' '
        IDETD   = ' '
        IDETL   = ' '
        IDETH   = ' '
        IDETR   = ' '
        FMOPT   = ' '  ! VSH
!        CRMODEL = '     '

!       Read FIRST line of simulation control
        REWIND(SCLun)

        LEVEL = 0
        FINDCH = '@N CON'
        DO WHILE (LEVEL /= CTRNO)
          CALL FIND (SCLun,FINDCH,LINEXP,IFIND)
          IF (IFIND == 1) THEN
!           Found a good section
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            IF (ISECT == 1) THEN
              READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
              IF (ERRNUM /= 0) RETURN
            ENDIF
          ELSE
            RETURN
          ENDIF
        ENDDO
          
!       Read simulation controls
        DO WHILE (ERRNUM == 0)
          CALL IGNORE2(SCLun,LINEXP,ISECT,CHARTEST)
          IF (ISECT == 0) EXIT
          SELECT CASE(CHARTEST(1:6))

!         First line of simulation controls
          CASE('@N GEN')
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
            IF (ERRNUM /= 0) EXIT
            IF (LEVEL /= CTRNO) EXIT 

!           READ (CHARTEST,55,IOSTAT=ERRNUM) NYRS,NREPSQ,ISIMI,
!     &           YRSIM,RRSEED1,TITSIM,CRMODEL
!  55       FORMAT (14X,2(1X,I5),5X,A1,1X,I5,1X,I5,1X,A25,1X,A8)

            READ (CHARTEST,'(15X,A5)',IOSTAT=ERRNUM) NYRS_txt
            CALL CHECK_I('NYRS', NYRS_txt, ERRNUM, CONTROL%NYRS, 
     &        MSG, NMSG, NYRS)

            READ (CHARTEST,'(21X,A5)',IOSTAT=ERRNUM) NREPSQ_txt
            CALL CHECK_I('NREPSQ', NREPSQ_txt, ERRNUM, 1,
     &        MSG, NMSG, NREPSQ)

            READ (CHARTEST,'(31X,A1)',IOSTAT=ERRNUM) ISIMI
            CALL CHECK_A('ISIMI', ISIMI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(33X,A5)',IOSTAT=YRSIM_ERR) YRSIM_txt
            CALL CHECK_I('YRSIM', YRSIM_txt, YRSIM_ERR, CONTROL%YRSIM,
     &        MSG, NMSG, YRSIM)

!            READ (CHARTEST,'(39X,I5)',IOSTAT=ERRNUM) RSEED1
!            CALL CHECK_I(ERRNUM, 'NYRS', NYRS, MSG, NMSG)

            READ (CHARTEST,'(71X,A8)',IOSTAT=ERRNUM) CTRMODEL
            CALL CHECK_A('CTRMODEL', CTRMODEL, ERRNUM, MSG, NMSG)

!         Second line of simulation controls
          CASE('@N OPT')
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
            IF (ERRNUM /= 0) EXIT
            IF (LEVEL /= CTRNO) EXIT 

!           READ (CHARTEST,60,IOSTAT=ERRNUM) LN,ISWWAT,ISWNIT,ISWSYM,
!     &         ISWPHO,ISWPOT,ISWDIS,ISWCHE,ISWTIL, ISWFWT
!  60       FORMAT (I3,11X,9(5X,A1))

            READ (CHARTEST,'(19X,A1)',IOSTAT=ERRNUM) ISWWAT
            CALL CHECK_A('ISWWAT', ISWWAT, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(25X,A1)',IOSTAT=ERRNUM) ISWNIT
            CALL CHECK_A('ISWNIT', ISWNIT, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(31X,A1)',IOSTAT=ERRNUM) ISWSYM
            CALL CHECK_A('ISWSYM', ISWSYM, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(37X,A1)',IOSTAT=ERRNUM) ISWPHO
            CALL CHECK_A('ISWPHO', ISWPHO, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(43X,A1)',IOSTAT=ERRNUM) ISWPOT
            CALL CHECK_A('ISWPOT', ISWPOT, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(49X,A1)',IOSTAT=ERRNUM) ISWDIS
            CALL CHECK_A('ISWDIS', ISWDIS, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(55X,A1)',IOSTAT=ERRNUM) ISWCHE
            CALL CHECK_A('ISWCHE', ISWCHE, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(61X,A1)',IOSTAT=ERRNUM) ISWTIL
            CALL CHECK_A('ISWTIL', ISWTIL, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(67X,A1)',IOSTAT=ERRNUM) ICO2
            CALL CHECK_A('ICO2  ', ICO2, ERRNUM, MSG, NMSG)

            ISWWAT = UPCASE(ISWWAT)
            ISWNIT = UPCASE(ISWNIT)
            ISWSYM = UPCASE(ISWSYM)
            ISWPHO = UPCASE(ISWPHO)
            ISWPOT = UPCASE(ISWPOT)
            ISWDIS = UPCASE(ISWDIS)
            ISWCHE = UPCASE(ISWCHE)
            ISWTIL = UPCASE(ISWTIL)
            ICO2   = UPCASE(ICO2)

!         Third line of simulation controls
          CASE('@N MET')
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
            IF (ERRNUM /= 0) EXIT
            IF (LEVEL /= CTRNO) EXIT 

!           READ (CHARTEST,61,IOSTAT=ERRNUM) LN,MEWTH,MESIC,
!    &           MELI,MEEVP,MEINF,MEPHO,MEHYD,NSWITCH, 
!    &           MESOM, MESEV, MESOL, METMP, MEGHG
! 61        FORMAT (I3,11X,7(5X,A1),5X,I1,5X,A1,2(5X,A1),5X,I1,)

            READ (CHARTEST,'(19X,A1)',IOSTAT=ERRNUM) MEWTH
            CALL CHECK_A('MEWTH', MEWTH, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(25X,A1)',IOSTAT=ERRNUM) MESIC
            CALL CHECK_A('MESIC', MESIC, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(31X,A1)',IOSTAT=ERRNUM) MELI
            CALL CHECK_A('MELI', MELI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(37X,A1)',IOSTAT=ERRNUM) MEEVP
            CALL CHECK_A('MEEVP', MEEVP, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(43X,A1)',IOSTAT=ERRNUM) MEINF
            CALL CHECK_A('MEINF', MEINF, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(49X,A1)',IOSTAT=ERRNUM) MEPHO
            CALL CHECK_A('MEPHO', MEPHO, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(55X,A1)',IOSTAT=ERRNUM) MEHYD
            CALL CHECK_A('MEHYD', MEHYD, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(61X,A1)',IOSTAT=ERRNUM) NSWITCH_txt
            CALL CHECK_I('NSWITCH', NSWITCH_txt, ERRNUM, ISWITCH%NSWI,
     &        MSG, NMSG, NSWITCH)

            READ (CHARTEST,'(67X,A1)',IOSTAT=ERRNUM) MESOM
            CALL CHECK_A('MESOM', MESOM, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(73X,A1)',IOSTAT=ERRNUM) MESEV
            CALL CHECK_A('MESEV', MESEV, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(79X,A1)',IOSTAT=ERRNUM) MESOL
            CALL CHECK_A('MESOL', MESOL, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(85X,A1)',IOSTAT=ERRNUM) METMP
            CALL CHECK_A('METMP', METMP, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(91X,A1)',IOSTAT=ERRNUM) MEGHG
            CALL CHECK_A('MEGHG', MEGHG, ERRNUM, MSG, NMSG)

            MEWTH = UPCASE(MEWTH)
            MESIC = UPCASE(MESIC)
            MELI  = UPCASE(MELI)
            MEEVP = UPCASE(MEEVP)
            MEINF = UPCASE(MEINF)
            MEPHO = UPCASE(MEPHO)
            MESOM = UPCASE(MESOM)
            MEHYD = UPCASE(MEHYD)
            MESEV = UPCASE(MESEV)
            METMP = UPCASE(METMP)
            MEGHG = UPCASE(MEGHG)

!         Fourth line of simulation controls
          CASE('@N MAN')
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
            IF (ERRNUM /= 0) EXIT
            IF (LEVEL /= CTRNO) EXIT 

!           READ (CHARTEST,60,IOSTAT=ERRNUM) LN,IPLTI,IIRRI,
!    &           IFERI,IRESI,IHARI
!  60       FORMAT (I3,11X,9(5X,A1))

            READ (CHARTEST,'(19X,A1)',IOSTAT=ERRNUM) IPLTI
            CALL CHECK_A('IPLTI', IPLTI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(25X,A1)',IOSTAT=ERRNUM) IIRRI
            CALL CHECK_A('IIRRI', IIRRI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(31X,A1)',IOSTAT=ERRNUM) IFERI
            CALL CHECK_A('IFERI', IFERI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(37X,A1)',IOSTAT=ERRNUM) IRESI
            CALL CHECK_A('IRESI', IRESI, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(43X,A1)',IOSTAT=ERRNUM) IHARI
            CALL CHECK_A('IHARI', IHARI, ERRNUM, MSG, NMSG)

            IPLTI = UPCASE(IPLTI)
            IIRRI = UPCASE(IIRRI)
            IFERI = UPCASE(IFERI)
            IRESI = UPCASE(IRESI)
            IHARI = UPCASE(IHARI)

!         Fifth line of simulation controls
          CASE('@N OUT')
            CALL IGNORE(SCLun,LINEXP,ISECT,CHARTEST)
            READ (CHARTEST,'(I2)',IOSTAT=ERRNUM) LEVEL
            IF (ERRNUM /= 0) EXIT
            IF (LEVEL /= CTRNO) EXIT 

!           READ (CHARTEST,65,IOSTAT=ERRNUM) LN,IOX,IDETO,
!    &      IDETS,FROP,IDETG,IDETC,IDETW,IDETN,IDETP,IDETD,
!    &      IDETL,IDETH,IDETR
! 65        FORMAT (I3,11X,3(5X,A1),4X,I2,9(5X,A1))

            READ (CHARTEST,'(19X,A1)',IOSTAT=ERRNUM) IOX
            CALL CHECK_A('FNAME', IOX, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(25X,A1)',IOSTAT=ERRNUM) IDETO
            CALL CHECK_A('IDETO', IDETO, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(31X,A1)',IOSTAT=ERRNUM) IDETS
            CALL CHECK_A('IDETS', IDETS, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(35X,A3)',IOSTAT=ERRNUM) FROP_txt
            CALL CHECK_I('FROP', FROP_txt, ERRNUM, CONTROL%FROP,
     &        MSG, NMSG, FROP)

            READ (CHARTEST,'(43X,A1)',IOSTAT=ERRNUM) IDETG
            CALL CHECK_A('IDETG', IDETG, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(49X,A1)',IOSTAT=ERRNUM) IDETC
            CALL CHECK_A('IDETC', IDETC, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(55X,A1)',IOSTAT=ERRNUM) IDETW
            CALL CHECK_A('IDETW', IDETW, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(61X,A1)',IOSTAT=ERRNUM) IDETN
            CALL CHECK_A('IDETN', IDETN, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(67X,A1)',IOSTAT=ERRNUM) IDETP
            CALL CHECK_A('IDETP', IDETP, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(73X,A1)',IOSTAT=ERRNUM) IDETD
            CALL CHECK_A('IDETD', IDETD, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(79X,A1)',IOSTAT=ERRNUM) IDETL
            CALL CHECK_A('IDETL', IDETL, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(85X,A1)',IOSTAT=ERRNUM) IDETH
            CALL CHECK_A('IDETH', IDETH, ERRNUM, MSG, NMSG)

            READ (CHARTEST,'(91X,A1)',IOSTAT=ERRNUM) IDETR
            CALL CHECK_A('IDETR', IDETR, ERRNUM, MSG, NMSG)
           
            ! VSH
            READ (CHARTEST,'(97X,A1)',IOSTAT=ERRNUM) FMOPT
            CALL CHECK_A('FMOPT', FMOPT, ERRNUM, MSG, NMSG)

            IOX   = UPCASE(IOX)
            IDETO = UPCASE(IDETO)
            IDETS = UPCASE(IDETS)
            IDETG = UPCASE(IDETG)
            IDETC = UPCASE(IDETC)
            IDETW = UPCASE(IDETW)
            IDETN = UPCASE(IDETN)
            IDETP = UPCASE(IDETP)
            IDETD = UPCASE(IDETD)
            IDETL = UPCASE(IDETL)
            IDETH = UPCASE(IDETH)
            IDETR = UPCASE(IDETR)
            FMOPT = UPCASE(FMOPT)  ! VSH

          END SELECT
        ENDDO

        CLOSE (SCLun)

        IF (NMSG < 6) THEN
          MSG(4)='No default simulation controls read.'
          NMSG = 4
          UseSimCtr = .FALSE.
        ELSE
          UseSimCtr = .TRUE.
        ENDIF
        CALL WARNING(NMSG,ERRKEY,MSG)
        CALL INFO (NMSG,ERRKEY,MSG)

      ELSE
        IF (.NOT. UseSimCtr) RETURN
        MEPHO  = MEPHO_SAVE
        ISWSYM = ISWSYM_SAVE
      ENDIF

!     Fill ISWITCH variable (complete)
      IF (IOX    /= ' ' .AND. IOX /= '.')    ISWITCH % FNAME  = IOX 
      IF (ISIMI  /= ' ' .AND. ISIMI  /= '.') ISWITCH % ISIMI  = ISIMI 
      IF (ISWWAT /= ' ' .AND. ISWWAT /= '.') ISWITCH % ISWWAT = ISWWAT
      IF (ISWNIT /= ' ' .AND. ISWNIT /= '.') ISWITCH % ISWNIT = ISWNIT
      IF (ISWSYM /= ' ' .AND. ISWSYM /= '.') ISWITCH % ISWSYM = ISWSYM
      IF (ISWPHO /= ' ' .AND. ISWPHO /= '.') ISWITCH % ISWPHO = ISWPHO
      IF (ISWPOT /= ' ' .AND. ISWPOT /= '.') ISWITCH % ISWPOT = ISWPOT
      IF (ISWDIS /= ' ' .AND. ISWDIS /= '.') ISWITCH % ISWDIS = ISWDIS
      IF (ISWCHE /= ' ' .AND. ISWCHE /= '.') ISWITCH % ISWCHE = ISWCHE
      IF (ISWTIL /= ' ' .AND. ISWTIL /= '.') ISWITCH % ISWTIL = ISWTIL
      IF (ICO2   /= ' ' .AND. ICO2   /= '.') ISWITCH % ICO2   = ICO2
      IF (MEWTH  /= ' ' .AND. MEWTH  /= '.') ISWITCH % MEWTH  = MEWTH
      IF (MESOM  /= ' ' .AND. MESOM  /= '.') ISWITCH % MESOM  = MESOM
      IF (MELI   /= ' ' .AND. MELI   /= '.') ISWITCH % MELI   = MELI 
      IF (MEEVP  /= ' ' .AND. MEEVP  /= '.') ISWITCH % MEEVP  = MEEVP
      IF (MEINF  /= ' ' .AND. MEINF  /= '.') ISWITCH % MEINF  = MEINF
      IF (MEPHO  /= ' ' .AND. MEPHO  /= '.') ISWITCH % MEPHO  = MEPHO
      IF (MEHYD  /= ' ' .AND. MEHYD  /= '.') ISWITCH % MEHYD  = MEHYD
      IF (MESEV  /= ' ' .AND. MESEV  /= '.') ISWITCH % MESEV  = MESEV
      IF (MESOL  /= ' ' .AND. MESOL  /= '.') ISWITCH % MESOL  = MESOL
      IF (METMP  /= ' ' .AND. METMP  /= '.') ISWITCH % METMP  = METMP
      IF (MEGHG  /= ' ' .AND. MEGHG  /= '.') ISWITCH % MEGHG  = MEGHG
      IF (IPLTI  /= ' ' .AND. IPLTI  /= '.') ISWITCH % IPLTI  = IPLTI
      IF (IIRRI  /= ' ' .AND. IIRRI  /= '.') ISWITCH % IIRRI  = IIRRI
      IF (IFERI  /= ' ' .AND. IFERI  /= '.') ISWITCH % IFERI  = IFERI
      IF (IRESI  /= ' ' .AND. IRESI  /= '.') ISWITCH % IRESI  = IRESI
      IF (IHARI  /= ' ' .AND. IHARI  /= '.') ISWITCH % IHARI  = IHARI
      IF (IDETO  /= ' ' .AND. IDETO  /= '.') ISWITCH % IDETO  = IDETO
      IF (IDETS  /= ' ' .AND. IDETS  /= '.') ISWITCH % IDETS  = IDETS
      IF (IDETG  /= ' ' .AND. IDETG  /= '.') ISWITCH % IDETG  = IDETG
      IF (IDETC  /= ' ' .AND. IDETC  /= '.') ISWITCH % IDETC  = IDETC
      IF (IDETW  /= ' ' .AND. IDETW  /= '.') ISWITCH % IDETW  = IDETW
      IF (IDETN  /= ' ' .AND. IDETN  /= '.') ISWITCH % IDETN  = IDETN
      IF (IDETP  /= ' ' .AND. IDETP  /= '.') ISWITCH % IDETP  = IDETP
      IF (IDETD  /= ' ' .AND. IDETD  /= '.') ISWITCH % IDETD  = IDETD
      IF (IDETL  /= ' ' .AND. IDETL  /= '.') ISWITCH % IDETL  = IDETL
      IF (IDETH  /= ' ' .AND. IDETH  /= '.') ISWITCH % IDETH  = IDETH
      IF (IDETR  /= ' ' .AND. IDETR  /= '.') ISWITCH % IDETR  = IDETR
      ! VSH
      IF (FMOPT  /= ' ' .AND. FMOPT  /= '.') ISWITCH % FMOPT  = FMOPT

      IF (NSWITCH /=-99) ISWITCH % NSWI   = NSWITCH
    
!       Fill CONTROL variable (partial)
      IF (MODEL(1:1) /= ' ' .AND. MODEL(1:1) /= '.') 
     &                                     CONTROL % MODEL = MODEL
!     IF (MESIC /= ' ' .AND. MESIC /= '.') CONTROL % MESIC = MESIC  

      IF (NYRS  /= -99) CONTROL % NYRS  = NYRS

!     Check YRSIM again because each simulation requires a check against FileX value.
!     (i.e., not just when control file is read for the first simulation in a batch.)
      IF (YRSIM > 0) THEN
        CALL CHECK_I(
     &    'YRSIM', YRSIM_txt, YRSIM_ERR, CONTROL%YRSIM,   !Input
     &    MSG, NMSG, YRSIM)                       !Output

        CALL Y4K_DOY (YRSIM,FILEX,LINEXP,ERRKEY,1)
        CALL YR_DOY (YRSIM,YEAR,ISIM)
        CONTROL % YRSIM = YRSIM
      ELSE
        CONTROL % YRSIM = YRSIM_SAVE
      ENDIF

      IF (FROP  > 0)    CONTROL % FROP  = FROP   

      RETURN
      END SUBROUTINE External_SimControls
!=======================================================================

      SUBROUTINE CHECK_A(LABEL, VALUE, ERRNUM, MSG, NMSG)
      IMPLICIT NONE
      EXTERNAL MSG_TEXT

      CHARACTER*(*) VALUE
      CHARACTER*(*) LABEL
      CHARACTER*30 MSG_TEXT
      CHARACTER*78 MSG(50)
      INTEGER ERRNUM, NMSG

      IF (ERRNUM /= 0)  THEN
        VALUE = ' '
      ENDIF

      IF (VALUE /= ' ' .AND. VALUE /= '.') THEN
        NMSG = NMSG + 1
        WRITE(MSG(NMSG),'(A8,A,A,2X,A30)') LABEL, " = ", VALUE, 
     &    MSG_TEXT(LABEL)
      ENDIF

      RETURN
      END SUBROUTINE CHECK_A

!=======================================================================

      SUBROUTINE CHECK_I(
     &  LABEL, txtVALUE, ERRNUM, FILEX_VALUE,   !Input
     &  MSG, NMSG, VALUE)                       !Output

      IMPLICIT NONE
      EXTERNAL MSG_TEXT

      CHARACTER*(*), INTENT(IN) :: LABEL
      CHARACTER*(*), INTENT(IN) :: txtVALUE
      INTEGER, INTENT(IN) :: ERRNUM, FILEX_VALUE
      CHARACTER*78, INTENT(INOUT) :: MSG(50)
      INTEGER, INTENT(INOUT) :: NMSG
      INTEGER, INTENT(OUT) :: VALUE

      INTEGER LENGTH
      CHARACTER*4 FMT
      CHARACTER*30 MSG_TEXT

      IF (ERRNUM /= 0)  THEN
        VALUE = FILEX_VALUE
        RETURN
      ENDIF

      IF (INDEX(txtVALUE,".") > 0) THEN
        VALUE = FILEX_VALUE
        RETURN
      ENDIF

      Length = LEN(TRIM(txtVALUE))
      WRITE(FMT,'(A,I1,A)') "(I", Length, ")"
      READ(txtValue, FMT) VALUE

      IF (VALUE > 0) THEN
        NMSG = NMSG + 1
        IF (VALUE < 10) THEN
          WRITE(MSG(NMSG),'(A8,A,I1,2X,A30)') LABEL," = ",VALUE, 
     &      MSG_TEXT(LABEL)  
        ELSE
          WRITE(MSG(NMSG),'(A8,A,I8,2X,A30)') LABEL," = ",VALUE, 
     &      MSG_TEXT(LABEL)  
        ENDIF
      ELSE
        VALUE = FILEX_VALUE
      ENDIF

      RETURN
      END SUBROUTINE CHECK_I

!=======================================================================

!=======================================================================
      CHARACTER*30 FUNCTION MSG_TEXT(LABEL)

      CHARACTER*(*) LABEL

      SELECT CASE(LABEL)  !    "123456789012345678901234567890"
      CASE('FNAME');  MSG_TEXT="Alternate file name option    "
      CASE('ISIMI');  MSG_TEXT="Start of simulation code      "
      CASE('ISWWAT'); MSG_TEXT="Soil water simulation switch  "
      CASE('ISWNIT'); MSG_TEXT="Soil N simulation switch      "
      CASE('ISWSYM'); MSG_TEXT="N fixation switch             "
      CASE('ISWPHO'); MSG_TEXT="P simulation switch           "
      CASE('ISWPOT'); MSG_TEXT="Potassium simulation switch   "
      CASE('ISWDIS'); MSG_TEXT="Pest & disease simulation     "
      CASE('ISWCHE'); MSG_TEXT="Chemical application switch   "
      CASE('ISWTIL'); MSG_TEXT="Tillage option switch         "
      CASE('ICO2');   MSG_TEXT="Option to read CO2 from file  "
      CASE('MEWTH');  MSG_TEXT="Weather method                "
      CASE('MESOM');  MSG_TEXT="Soil organic matter method    "
      CASE('MELI') ;  MSG_TEXT="Light interception method     "
      CASE('MEEVP');  MSG_TEXT="Pot. evapotranspiration method"
      CASE('MEINF');  MSG_TEXT="Infiltration method           "
      CASE('MEPHO');  MSG_TEXT="Photosynthesis method         "
      CASE('MEHYD');  MSG_TEXT="Hydrology method              "
      CASE('MESEV');  MSG_TEXT="Soil evaporation method       "
      CASE('MESOL');  MSG_TEXT="Soil input and partitioning   "
      CASE('METMP');  MSG_TEXT="Soil temperature method       "
      CASE('MEGHG');  MSG_TEXT="Greenhouse gas calc method    "
      CASE('IPLTI');  MSG_TEXT="Planting method switch        "
      CASE('IIRRI');  MSG_TEXT="Irrigation method switch      "
      CASE('IFERI');  MSG_TEXT="Fertilizer switch             "
      CASE('IRESI');  MSG_TEXT="Organic matter switch         "
      CASE('IHARI');  MSG_TEXT="Harvest simulation switch     "
      CASE('IDETO');  MSG_TEXT="Overview output switch        "
      CASE('IDETS');  MSG_TEXT="Summary output switch         "
      CASE('IDETG');  MSG_TEXT="Growth output switch          "
      CASE('IDETC');  MSG_TEXT="Carbon output switch          "
      CASE('IDETW');  MSG_TEXT="Water output switch           "
      CASE('IDETN');  MSG_TEXT="Nitrogen output switch        "
      CASE('IDETP');  MSG_TEXT="Phosphorus output switch      "
      CASE('IDETD');  MSG_TEXT="Pest & disease output switch  "
      CASE('IDETL');  MSG_TEXT="Output detail switch          "
      CASE('IDETH');  MSG_TEXT="Chemical output file switch   "
      CASE('IDETR');  MSG_TEXT="Operations output file switch "
      CASE('FMOPT');  MSG_TEXT="Format options switch (CSV)   "
      CASE('NSWITCH');MSG_TEXT="Nitrogen options switch       "
      CASE('NYRS')  ; MSG_TEXT="Number of years of simulation "
      CASE('YRSIM') ; MSG_TEXT="Start of simulation date      "
      CASE('MODEL') ; MSG_TEXT="Crop model                    "
      CASE('MESIC') ; MSG_TEXT="Sequence code (not used)      "
      CASE('FROP')  ; MSG_TEXT="Frequency of output code      "
      CASE DEFAULT;   MSG_TEXT="                              "
      END SELECT

      RETURN
      END FUNCTION MSG_TEXT
!=======================================================================
