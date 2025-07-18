!***********************************************************************
!  OPSOMLIT_C, subroutine for CENTURY-based SOM/residue module of DSSAT.
!
!  Purpose: Prints daily output of SOM and litter variables with all
!           variables on one line per day (easy for importing in a
!           spreadsheet). See SOMLITPRINT for layer-by-layer output.
!
!  Revision history:
!  01/01/2000 AJG written
!  06/23/2003 CHP split into two files and only print layers 0 thru 5.  
!                 Most text editors can't handle wide files.
!  10/17/2005 CHP Revised output to include all surface pools and total 
!                 SOM + LIT C and N
!                 Added total soil C at 0-20cm and 20-40cm depth.
!  06/06/2006 CHP Added total soil N at 0-20cm and 20-40cm depth.
!  10/02/2007 CHP Added C:N output file (temp?)
!
!  Called: CENTURY
!  Calls: --
!***********************************************************************

      SUBROUTINE OPSOMLIT_C (CONTROL, ISWITCH,
     &  ACCCO2, LITC, LITE, METABC, METABE,               !Input
     &  N_ELEMS,OMAData, SOILPROP, SOM1C, SOM1E, SOM2C,   !Input
     &  SOM2E, SOM23E, SOM3C, SOM3E, SomLitC, SomLitE,    !Input
     &  STRUCC, STRUCE, TLITC, TLITE, TMETABC, TMETABE,   !Input
     &  TSOM1C, TSOM1E, TSOM2C, TSOM2E, TSOM23E,          !Input
     &  TSOM3C, TSOM3E, TSOMC, TSOME, TSTRUCC, TSTRUCE)   !Input

!     ------------------------------------------------------------------
      USE ModuleDefs     !Definitions of constructed variable types, 
                         !which contain control information, soil
                         !parameters, hourly weather data.
      ! VSH
      USE CsvOutput 
      USE Linklist
      IMPLICIT  NONE
      EXTERNAL GETLUN, HEADER, YR_DOY, SUMVALS, INCDAT
      SAVE
!     ------------------------------------------------------------------

      CHARACTER*1 RNMODE
      CHARACTER*8 LayerText(11)
      CHARACTER*11 OUTSOMC, OUTSOMN, OUTSOMP

      INTEGER DAS, DYNAMIC, FROP, INCDAT, L, N_ELEMS
      INTEGER NOUTDC, NOUTDN, NOUTDP 
      INTEGER RUN, YRDOY, YEAR, DOY, REPNO, RUNNO
      INTEGER, PARAMETER :: SRFC = 0, SOIL = 1
      INTEGER NLAYR
!     REAL, DIMENSION(5) :: SL, S1, S2, S3, LIT, MET, STR
      REAL, DIMENSION(5) :: TC, S1C, S2C, S3C, LIT, MET, STR
      REAL, DIMENSION(5) :: TN, S1N, S2N, S3N, LIN, MEN, STN
      REAL, DIMENSION(5) :: TP, S1P, S2P, S3P, LIP, MEP, STP

      REAL CUMRESC, TLITC, TMETABC, TSOM1C, TSOM2C,
     &  TSOM3C, TSOMC, TSTRUCC
      REAL SOC_20CM, SOC_20CM_P, SOC_40CM, SOC_40CM_P, FRAC
      REAL SON_20CM, SON_20CM_P, SON_40CM, SON_40CM_P
      REAL SOP_20CM, SOP_20CM_P, SOP_40CM, SOP_40CM_P
      REAL SOIL_20CM, SOIL_40CM
      REAL TCTD, TC0D, TCSD
      REAL TNTD, TN0D, TNSD 

      REAL SLC_20CM, SLC_20CM_P, SLC_40CM, SLC_40CM_P

      REAL ACCCO2(0:1), CUMRESE(NELEM), TMETABE(NELEM), 
     &   TSOM2E(NELEM),TSOM23E(NELEM), 
     &   TSOM3E(NELEM), TSOME(NELEM), TSTRUCE(NELEM)

      REAL TSOM1E(NELEM), TLITE(NELEM)

      REAL LITC(0:NL), METABC(0:NL), SOM1C(0:NL), SOM2C(NL),
     &  SOM3C(NL), STRUCC(0:NL)    !, SSOMC(NL)
      REAL BD(NL), DLAYR(NL), DS(NL)

      REAL LITE(0:NL,3), METABE(0:NL,3), SOM1E(0:NL,3), SOM2E(NL,3),
     &  SOM23E(NL,3), SOM3E(NL,3), STRUCE(0:NL,3) !, SSOME(0:NL,3)
      REAL SomLitC(0:NL), SomLitE(0:NL,NELEM)

      LOGICAL DOPRINT, FEXIST, PRINTC, PRINTN, PRINTP

!!     C:N ratios:
!      CHARACTER*11 OUTCN
!      INTEGER NOUTCN
!      REAL TCNTD, TCN0D, TCNSD
!      REAL S1CN0D, S1CNSD, S2CNSD, S3CNSD
!      REAL LCN0D, LCNSD, MECN0D, MECNSD, STCN0D, STCNSD
!      REAL, DIMENSION(5) :: TCN,S1CN,S2CN,S3CN,LCN,MECN,STCN

!     Arrays which contain data for printing in SUMMARY.OUT file
      INTEGER, PARAMETER :: SUMNUM = 5
      CHARACTER*5, DIMENSION(SUMNUM) :: LABEL
      REAL, DIMENSION(SUMNUM) :: VALUE

!!==================================================================
!     Define constructed variable types based on definitions in
!     ModuleDefs.for.
      TYPE (ControlType)   CONTROL
      TYPE (SwitchType)    ISWITCH
      TYPE (OrgMatAppType) OMAData    !Organic matter application
      TYPE (SoilType)      SOILPROP

!     IDETL = 'N' or '0' (zero) -- supress output
      IF (INDEX('N0',ISWITCH % IDETL) > 0) RETURN

!     Transfer values from constructed data types into local variables.
      DAS     = CONTROL % DAS
      DYNAMIC = CONTROL % DYNAMIC
      FROP    = CONTROL % FROP
      RUN     = CONTROL % RUN
      RNMODE  = CONTROL % RNMODE
      REPNO   = CONTROL % REPNO
      YRDOY   = CONTROL % YRDOY

      BD    = SOILPROP % BD
      DS    = SOILPROP % DS
      DLAYR = SOILPROP % DLAYR
      NLAYR = SOILPROP % NLAYR
      
      FMOPT  = ISWITCH % FMOPT    ! VSH
!***********************************************************************
!***********************************************************************
!     INPUT + RUNINIT
!***********************************************************************
      IF (DYNAMIC == RUNINIT) THEN
!     ------------------------------------------------------------------
      IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
!     SOM daily output file
      OUTSOMC = 'SOMLITC.OUT'
      OUTSOMN = 'SOMLITN.OUT'
      CALL GETLUN('OUTSOMC', NOUTDC)
      CALL GETLUN('OUTSOMN', NOUTDN)
      END IF    ! VSH

      IF (N_ELEMS > 1) THEN
        OUTSOMP = 'SOMLITP.OUT'
        CALL GETLUN('OUTSOMP', NOUTDP)
      ENDIF

      PRINTC = .FALSE.
      PRINTN = .FALSE.
      PRINTP = .FALSE.

!***********************************************************************
!***********************************************************************
!     SEASONAL INITIALIZATION
!***********************************************************************
      ELSEIF (DYNAMIC == SEASINIT) THEN
!     ------------------------------------------------------------------
      IF (ISWITCH % IDETC == 'Y') PRINTC = .TRUE.
      IF (ISWITCH % IDETN == 'Y' .AND. N_ELEMS > 0) PRINTN = .TRUE.
      IF (ISWITCH % IDETP == 'Y' .AND. N_ELEMS > 1) PRINTP = .TRUE.
      
      IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
      IF (PRINTC) THEN
!       Open SOMC output file and print headers.
        INQUIRE (FILE = OUTSOMC, EXIST = FEXIST)
        IF (FEXIST) THEN
          OPEN (UNIT = NOUTDC, FILE = OUTSOMC, STATUS = 'OLD',
     &      POSITION = 'APPEND')
        ELSE
          OPEN (UNIT = NOUTDC, FILE = OUTSOMC, STATUS = 'NEW')
          WRITE(NOUTDC,'("*SOM C DAILY OUTPUT FILE")')
        ENDIF
      ENDIF
      END IF    ! VSH

      IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
      IF (PRINTN) THEN
!       Open SOM-N output file and print headers.
        INQUIRE (FILE = OUTSOMN, EXIST = FEXIST)
        IF (FEXIST) THEN
          OPEN (UNIT = NOUTDN, FILE = OUTSOMN, STATUS = 'OLD',
     &      POSITION = 'APPEND')
        ELSE
          OPEN (UNIT = NOUTDN, FILE = OUTSOMN, STATUS = 'NEW')
          WRITE(NOUTDN,'("*SOM N DAILY OUTPUT FILE")')
        ENDIF

      ENDIF
      END IF    ! VSH
      
      IF (PRINTP) THEN
!       Open SOM-P output file and print headers.
        INQUIRE (FILE = OUTSOMP, EXIST = FEXIST)
        IF (FEXIST) THEN
          OPEN (UNIT = NOUTDP, FILE = OUTSOMP, STATUS = 'OLD',
     &      POSITION = 'APPEND')
        ELSE
          OPEN (UNIT = NOUTDP, FILE = OUTSOMP, STATUS = 'NEW')
          WRITE(NOUTDP,'("*SOM P DAILY OUTPUT FILE")')
        ENDIF
      ENDIF

      IF (RNMODE .NE. 'Q' .OR. RUN == 1) THEN
        IF (RNMODE == 'Q') THEN
          !For first run of a sequenced run, use replicate
          ! number instead of run number in header.
          RUNNO = REPNO
        ELSE
          RUNNO = RUN
        ENDIF

!       LayerText, from SoilDyn, contains depth labels for soil layers
        LayerText = SOILPROP % LayerText
!       LayerText(11) contains data from layers 5 thru NLAYR
        IF (NLAYR > 4) THEN
          LayerText(5) = SOILPROP % LayerText(11)
        ENDIF
        
        IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
        IF (PRINTC) THEN
          CALL HEADER(SEASINIT, NOUTDC, RUNNO)
          WRITE (NOUTDC, 100) 
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5)
          WRITE (NOUTDC, 200)
        ENDIF

        IF (PRINTN) THEN
          CALL HEADER(SEASINIT, NOUTDN, RUNNO)
          WRITE (NOUTDN, 110) 
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5)
          WRITE (NOUTDN, 210)

        ENDIF
        END IF    ! VSH
        
        IF (PRINTP) THEN
          CALL HEADER(SEASINIT, NOUTDP, RUNNO)
          WRITE (NOUTDP,120)
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5),
     &      (LayerText(L), L=1,5),(LayerText(L), L=1,5)
          WRITE (NOUTDP,220)
        ENDIF
      ENDIF

      ENDIF !DYNAMIC=SEASINIT

!***********************************************************************
!***********************************************************************
!     OUTPUT
!***********************************************************************
      DOPRINT = .FALSE.
      SELECT CASE (DYNAMIC)
      CASE (SEASINIT)
        IF (INDEX('FQ',RNMODE) < 1 .OR. RUN == 1) DOPRINT = .TRUE.
        CALL YR_DOY(INCDAT(YRDOY,-1),YEAR,DOY)

      CASE (OUTPUT)
        IF (MOD(DAS,FROP) == 0) DOPRINT = .TRUE.
        IF (.NOT. DOPRINT) RETURN
        CALL YR_DOY(YRDOY, YEAR, DOY)

      CASE (SEASEND)
        IF (MOD(DAS,FROP) /= 0) DOPRINT = .TRUE.
        IF (.NOT. DOPRINT) GO TO 5000
        CALL YR_DOY(YRDOY, YEAR, DOY)
      END SELECT

      CumResE = OMAData % CumResE
      CumResC = 0.40 * OMAData % CumResWt

      TCTD = SomLitC(0) + TSOMC + TLITC
      TC0D = SomLitC(0)
      TCSD = TSOMC + TLITC

!     Carbon
!     Layer 5 includes all SOM and Lit C to bottom of profile
      TC = 0.; S1C = 0.; S2C = 0.; S3C = 0.; LIT = 0.; MET = 0.;STR = 0.
      DO L = 1, NLAYR
        SELECT CASE(L)
        CASE(1:5)
          TC(L)  = SomLitC(L)
          S1C(L) = SOM1C(L)
          S2C(L) = SOM2C(L)
          S3C(L) = SOM3C(L)
          LIT(L) = LITC(L)
          MET(L) = METABC(L)
          STR(L) = STRUCC(L)
        CASE(6:)
          TC(5)  = TC(5)  + SomLitC(L)
          S1C(5) = S1C(5) + SOM1C(L)
          S2C(5) = S2C(5) + SOM2C(L)
          S3C(5) = S3C(5) + SOM3C(L)
          LIT(5) = LIT(5) + LITC(L)
          MET(5) = MET(5) + METABC(L)
          STR(5) = STR(5) + STRUCC(L)
        END SELECT
      ENDDO

!     Calculate sample carbon from 0-20 cm and from 20-40 cm
!       in kg/ha and percent
      SOC_20CM = SOM1C(0)+ SOM1C(1) + SOM2C(1) + SOM3C(1)
      SLC_20CM = SOC_20CM + LITC(1)
      SON_20CM = SOM1E(0,1)+ SOM1E(1,1) + SOM2E(1,1) + SOM3E(1,1)
      SOP_20CM = SOM1E(0,2)+ SOM1E(1,2) + SOM23E(1,2)
      SOIL_20CM = DLAYR(1) * BD(1) * 1.E5

      SOC_40CM = 0.0
      SLC_40CM = 0.0
      SON_40CM = 0.0
      SOP_40CM = 0.0
      SOIL_40CM = 0.0

      DO L = 2, NLAYR
        IF (DS(L) <= 20.) THEN
!         Entire layer is in top 20 cm
          SOC_20CM = SOC_20CM + SOM1C(L) + SOM2C(L) + SOM3C(L)
          SLC_20CM = SLC_20CM + SOM1C(L) + SOM2C(L) + SOM3C(L) + LITC(L)
          SON_20CM = SON_20CM + SOM1E(L,1)+SOM2E(L,1)+SOM3E(L,1)
          SOP_20CM = SOP_20CM + SOM1E(L,2)+SOM23E(L,2)
          SOIL_20CM = SOIL_20CM + DLAYR(L) * BD(L) * 1.E5

        ELSEIF (DS(L-1) < 20.) THEN
!         A portion (FRAC) of layer is in top 20 cm
          FRAC = (20. - DS(L-1)) / DLAYR(L)
          SOC_20CM =SOC_20CM + FRAC*(SOM1C(L)+SOM2C(L)+SOM3C(L))
          SLC_20CM =SLC_20CM + FRAC*(SOM1C(L)+SOM2C(L)+SOM3C(L)+LITC(L))
          SON_20CM =SON_20CM + FRAC*(SOM1E(L,1)+SOM2E(L,1)+SOM3E(L,1))
          SOP_20CM =SOP_20CM + FRAC*(SOM1E(L,2)+SOM23E(L,2))
          SOIL_20CM = SOIL_20CM + FRAC * DLAYR(L) * BD(L) * 1.E5

          IF (DS(L) < 40.) THEN
!           The remaining portion (1 - FRAC) is between 20-40cm
            SOC_40CM =(1. - FRAC)*(SOM1C(L) + SOM2C(L)+SOM3C(L))
            SLC_40CM =(1. - FRAC)*(SOM1C(L) + SOM2C(L)+SOM3C(L)+LITC(L))
            SON_40CM =(1. - FRAC)*(SOM1E(L,1)+SOM2E(L,1)+SOM3E(L,1))
            SOP_40CM =(1. - FRAC)*(SOM1E(L,2)+SOM23E(L,2))
            SOIL_40CM=(1. - FRAC)* DLAYR(L) * BD(L) * 1.E5

          ELSE
!           Part of the remaining portion is between 20-40 cm
            FRAC = 20. / DLAYR(L)
            SOC_40CM = FRAC * (SOM1C(L) + SOM2C(L) + SOM3C(L))
            SLC_40CM = FRAC * (SOM1C(L) + SOM2C(L) + SOM3C(L) + LITC(L))
            SON_40CM = FRAC * (SOM1E(L,1) + SOM2E(L,1) + SOM3E(L,1))
            SOP_40CM = FRAC * (SOM1E(L,2) + SOM23E(L,2))
            SOIL_40CM= FRAC * DLAYR(L) * BD(L) * 1.E5
          ENDIF

        ELSEIF (DS(L) <= 40.) THEN
!         The entire layer is between 20-40 cm
          SOC_40CM = SOC_40CM + SOM1C(L) + SOM2C(L) + SOM3C(L)
          SLC_40CM = SLC_40CM + SOM1C(L) + SOM2C(L) + SOM3C(L)+ LITC(L)
          SON_40CM = SON_40CM + SOM1E(L,1) + SOM2E(L,1) + SOM3E(L,1)
          SOP_40CM = SOP_40CM + SOM1E(L,2) + SOM23E(L,2) 
          SOIL_40CM = SOIL_40CM + DLAYR(L) * BD(L) * 1.E5

        ELSEIF (DS(L-1) < 40.) THEN
!         A portion (FRAC) of layer is between 20-40 cm
          FRAC = (40. - DS(L-1)) / DLAYR(L)
          SOC_40CM = SOC_40CM +FRAC*(SOM1C(L)+SOM2C(L)+SOM3C(L))
          SLC_40CM = SLC_40CM +FRAC*(SOM1C(L)+SOM2C(L)+SOM3C(L)+LITC(L))
          SON_40CM = SON_40CM +FRAC*(SOM1E(L,1)+SOM2E(L,1)+SOM3E(L,1))
          SOP_40CM = SOP_40CM +FRAC*(SOM1E(L,2)+SOM23E(L,2))
          SOIL_40CM= SOIL_40CM + FRAC * DLAYR(L) * BD(L) * 1.E5
        ENDIF
      ENDDO

      SOC_20CM_P = SOC_20CM / SOIL_20CM * 100.
      SLC_20CM_P = SLC_20CM / SOIL_20CM * 100.
      SON_20CM_P = SON_20CM / SOIL_20CM * 100.
      SOP_20CM_P = SOP_20CM / SOIL_20CM * 100.
      SOC_40CM_P = SOC_40CM / SOIL_40CM * 100.
      SLC_40CM_P = SLC_40CM / SOIL_40CM * 100.
      SON_40CM_P = SON_40CM / SOIL_40CM * 100.
      SOP_40CM_P = SOP_40CM / SOIL_40CM * 100.

      IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
      IF (PRINTC) THEN
        WRITE (NOUTDC, 300) YEAR, DOY, DAS,  
     &    NINT(SOC_20CM), SOC_20CM_P, 
     &    NINT(SOC_40CM), SOC_40CM_P,
     &    NINT(SLC_20CM), SLC_20CM_P, 
     &    NINT(SLC_40CM), SLC_40CM_P,
     &    NINT(TCTD), NINT(TC0D), NINT(TCSD), (NINT(TC(L)), L=1,5),
     &    NINT(SOM1C(0)), NINT(TSOM1C), (NINT(S1C(L)), L=1, 5),
     &                    NINT(TSOM2C), (NINT(S2C(L)), L=1, 5), 
     &                    NINT(TSOM3C), (NINT(S3C(L)), L=1, 5),
     &    NINT(LITC(0)),  NINT(TLITC),  (NINT(LIT(L)), L=1, 5), 
     &    NINT(METABC(0)),NINT(TMETABC),(NINT(MET(L)),L=1, 5),
     &    NINT(STRUCC(0)),NINT(TSTRUCC),(NINT(STR(L)),L=1, 5), 
     &    NINT(CUMRESC), NINT(ACCCO2(SRFC)), NINT(ACCCO2(SOIL))
  300   FORMAT (1X,I4,1X,I3.3,1X,I5, 4(I8,F8.3), I10, 60(I8))
      ENDIF
      END IF    ! VSH
      
!     Nitrogen
!     Layer 5 includes all SOM and Lit N to bottom of profile
      IF (PRINTN) THEN
        TN = 0.; S1N = 0.; S2N = 0.; S3N = 0.; LIN = 0.;MEN = 0.;STN =0.
        DO L = 1, NLAYR
          SELECT CASE(L)
          CASE(1:5)
            TN(L)  = SomLitE(L,N)
            S1N(L) = SOM1E(L,N)
            S2N(L) = SOM2E(L,N)
            S3N(L) = SOM3E(L,N)
            LIN(L) = LITE(L,N)
            MEN(L) = METABE(L,N)
            STN(L) = STRUCE(L,N)
          CASE(6:)
            TN(5)  = TN(5)  + SomLitE(L,N)
            S1N(5) = S1N(5) + SOM1E(L,N)
            S2N(5) = S2N(5) + SOM2E(L,N)
            S3N(5) = S3N(5) + SOM3E(L,N)
            LIN(5) = LIN(5) + LITE(L,N)
            MEN(5) = MEN(5) + METABE(L,N)
            STN(5) = STN(5) + STRUCE(L,N)
          END SELECT
        ENDDO

        TNTD = SomLitE(0,N) + TSOME(N) + TLITE(N)
        TN0D = SomLitE(0,N)
        TNSD = TSOME(N) + TLITE(N)
        
        IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
        WRITE (NOUTDN, 310) YEAR, DOY, DAS, 
     &    NINT(SON_20CM), SON_20CM_P, 
     &    NINT(SON_40CM), SON_40CM_P,
     &    NINT(TNTD), NINT(TN0D), NINT(TNSD), (NINT(TN(L)), L=1, 5),
     &    NINT(SOM1E(0,N)),  NINT(TSOM1E(N)),(NINT(S1N(L)), L=1, 5), 
     &    NINT(TSOM2E(N)), (NINT(S2N(L)), L=1, 5), 
     &    NINT(TSOM3E(N)), (NINT(S3N(L)), L=1, 5), 
     &    LITE(0,N),   TLITE(N),   (LIN(L), L=1, 5), 
     &    METABE(0,N), TMETABE(N), (MEN(L), L=1, 5), 
     &    STRUCE(0,N), TSTRUCE(N), (STN(L), L=1, 5), 
     &    NINT(CUMRESE(N))
  310   FORMAT (1X,I4,1X,I3.3,1X,I5, 2(I8,F8.3), 27I8, 21F8.2, I8)
        END IF    ! VSH
        
!     VSH CSV output corresponding to somlitn.out
!       and SOMLITC.OUT CHP
      IF (FMOPT == 'C') THEN
       Call CsvOutSomC(EXPNAME, RUN, CONTROL%TRTNUM,
     & CONTROL%ROTNUM, CONTROL%REPNO, YEAR, DOY, DAS,  
     & SOC_20CM, SOC_20CM_P, SOC_40CM, SOC_40CM_P,
     & SLC_20CM, SLC_20CM_P, SLC_40CM, SLC_40CM_P,
     & TCTD, TC0D, TCSD, TC,
     & SOM1C, TSOM1C, S1C, TSOM2C, S2C, TSOM3C, S3C, LITC, TLITC, LIT, 
     & METABC, TMETABC, MET, STRUCC, TSTRUCC, STR, CUMRESC, 
     & ACCCO2, NL, vCsvlineSomC, vpCsvlineSomC, vlngthSomC)

       CALL LinklstSomC(vCsvlineSomC)

       Call CsvOutSomN(EXPNAME, RUN, CONTROL%TRTNUM,
     & CONTROL%ROTNUM, CONTROL%REPNO, YEAR, DOY, DAS,  
     & SON_20CM, SON_20CM_P, SON_40CM, SON_40CM_P, TNTD, TN0D, TNSD, TN,
     & SOM1E, TSOM1E, S1N, TSOM2E, S2N, TSOM3E, S3N, LITE, TLITE, LIN,
     & METABE, TMETABE, MEN, STRUCE, TSTRUCE, STN, CUMRESE, NL,N,NELEM,
     & vCsvlineSomN, vpCsvlineSomN, vlngthSomN)
       CALL LinklstSomN(vCsvlineSomN)
      END IF

      ENDIF

!     Phosphorus
      IF (PRINTP) THEN
!       Layer 5 includes all SOM and Lit P to bottom of profile
        TP = 0.;S1P = 0.;S2P = 0.;S3P = 0.;LIP = 0.; MEP = 0.; STP = 0.
        DO L = 1, NLAYR
          SELECT CASE(L)
          CASE(1:5)
            TP(L)  = SomLitE(L,P)
            S1P(L) = SOM1E(L,P)
            S2P(L) = SOM23E(L,P)
            LIP(L) = LITE(L,P)
            MEP(L) = METABE(L,P)
            STP(L) = STRUCE(L,P)
          CASE(6:)
            TP(5)  = TP(5)  + SomLitE(L,P)
            S1P(5) = S1P(5) + SOM1E(L,P)
            S2P(5) = S2P(5) + SOM23E(L,P)
            LIP(5) = LIP(5) + LITE(L,P)
            MEP(5) = MEP(5) + METABE(L,P)
            STP(5) = STP(5) + STRUCE(L,P)
          END SELECT
        ENDDO

        WRITE (NOUTDP, 320) YEAR, DOY, DAS, 
     &    NINT(SOP_20CM), SOP_20CM_P, 
     &    NINT(SOP_40CM), SOP_40CM_P,
     &    SomLitE(0,P)+TSOME(P)+TLITE(P), SomLitE(0,P), 
     &         TSOME(P)+TLITE(P), (TP(L),  L=1, 5), 
     &    SOM1E(0,P),  TSOM1E(P), (S1P(L), L=1, 5), 
     &    TSOM23E(P),             (S2P(L), L=1, 5), 
     &    LITE(0,P),   TLITE(P),  (LIP(L), L=1, 5), 
     &    METABE(0,P), TMETABE(P),(MEP(L), L=1, 5), 
     &    STRUCE(0,P), TSTRUCE(P),(STP(L), L=1, 5), 
     &    CUMRESE(P)
  320   FORMAT (1X,I4,1X,I3.3,1X,I5,  2(I8,F8.4), 50(F8.2))
      ENDIF

 5000 CONTINUE
!***********************************************************************
!***********************************************************************
!     SEASEND
!***********************************************************************
      IF (DYNAMIC == SEASEND) THEN
!     ------------------------------------------------------------------
        IF (FMOPT == 'A' .OR. FMOPT == ' ') THEN    ! VSH
        CLOSE (NOUTDC)
        CLOSE (NOUTDN)
        END IF    ! VSH
        
        CLOSE (NOUTDP)

!       Store Summary.out labels and values in arrays to send to
!       OPSUM routines for printing.  Integers are temporarily 
!       saved aS real numbers for placement in real array.
        LABEL(1)  = 'RECM '; VALUE(1)  = CUMRESC
!        LABEL(2)  = 'OCAM'; VALUE(2)  = TSOMC/1000.
!        12/01/2005 Wageningen CHP Report total C surface and soil -- 
!          this is important for C sequestration studies.
!        LABEL(2)  = 'OCAM'; VALUE(2) = (TSOMC + TLITC +SOMLITC(0))/1000.
!       12/12/2005 CHP Add OCTAM and ONTAM variables
        LABEL(2)  = 'OCTAM'; VALUE(2) = SomLitC(0) + TSOMC + TLITC
        LABEL(3)  = 'OCAM '; VALUE(3) = TSOMC + TLITC 
        LABEL(4)  = 'ONTAM'; VALUE(4) = SomLitE(0,1) +TSOME(1) +TLITE(1)
        LABEL(5)  = 'ONAM '; VALUE(5) = TSOME(1) + TLITE(1) 

        !Send labels and values to OPSUM
        CALL SUMVALS (SUMNUM, LABEL, VALUE) 

!***********************************************************************
!***********************************************************************
!     END OF DYNAMIC IF CONSTRUCT
!***********************************************************************
      ENDIF

100   FORMAT(
     &'!',468(' '),'Cumul.',/,'!',T17,
     &'<---- SOM C in top layers ----> ',
     &'<- SOM + LIT C in top layers -> <--',
     &'---------- Total Soil Organic Carbon (SOM + LIT) ------------> ',
     &'<--------- Active Soil Organic Carbon (SOM1) ---------> ',
     &'<---- Intermediate Soil Organic C (SOM2) -----> ',
     &'<------- Passive Soil Organic C (SOM3) -------> ',
     &'<------------------ Litter Carbon --------------------> ',
     &'<-------------- Metabolic Litter Carbon --------------> ',
     &'<------------- Structural Litter Carbon --------------> ',
     &' Resid.  <-Accum. CO2->',/,'!',T17,
     &'20cm-kg  20cm-% 40cm-kg  40cm-% ',
     &'20cm-kg  20cm-% 40cm-kg  40cm-%     Total',
     &' Surface    Soil',5A8,   !Total  
     &' Surface    Soil',5A8,   !Active
     &        '    Soil',5A8,   !Intermediate
     &        '    Soil',5A8,   !Passive
     &' Surface    Soil',5A8,   !Litter
     &' Surface    Soil',5A8,   !Metabolic
     &' Surface    Soil',5A8,   !Structural
     &' (kg/ha) Surface    Soil')

110   FORMAT(
     &'!',432(' '),'Cumul.',/,'!',T17,
     &'<---- SOM N in top layers ----> <----------------',
     &' Total Soil Organic Nitrogen ----------------> ',
     &'<-------- Active Soil Organic Nitrogen (SOM1) --------> ',
     &'<---- Intermediate Soil Organic N (SOM2) -----> ',
     &'<------- Passive Soil Organic N (SOM3) -------> ',
     &'<----------------- Litter Nitrogen -------------------> ',
     &'<------------- Metabolic Litter Nitrogen -------------> ',
     &'<------------ Structural Litter Nitrogen -------------> ',
     &' Res. N',/,'!',T17,
     &'20cm-kg  20cm-% 40cm-kg  40cm-%   Total',
     &' Surface    Soil',5A8,   !Total    
     &' Surface    Soil',5A8,   !Active
     &        '    Soil',5A8,   !Intermediate
     &        '    Soil',5A8,   !Passive
     &' Surface    Soil',5A8,   !Litter
     &' Surface    Soil',5A8,   !Metabolic
     &' Surface    Soil',5A8,   !Structural
     &' (kg/ha)')

120   FORMAT(
     &'!',352(' '),'Cumul.',/,'!',T17,
     &'<---- SOM P in top layers ----> ',
     &'<--------------- Total Soil Organic Phosphorus ---------',
     &'------> ',
     &'<------- Active Soil Organic Phosphorus (SOM1) -------> ',
     &'<-- Stable Soil Organic Phosphorus (SOM23) ---> ',
     &'<--------------------- Litter P ----------------------> ',
     &'<----------------- Metabolic Litter P ----------------> ',
     &'<---------------- Structural Litter P ----------------> ',
     &' Res. P',/,'!',T17,
     &'20cm-kg  20cm-% 40cm-kg  40cm-%   Total',
     &' Surface    Soil',5A8,   !Total    
     &' Surface    Soil',5A8,   !Active
     &        '    Soil',5A8,   !Stable
     &' Surface    Soil',5A8,   !Litter
     &' Surface    Soil',5A8,   !Metabolic
     &' Surface    Soil',5A8,   !Structural
     &' (kg/ha)')

200     FORMAT ('@YEAR DOY   DAS',
     &    '  SCS20D  SC%20D  SCS40D  SC%40D',
     &    '  SLC20D  SL%20D  SLC40D  SL%40D      SOCD',
     &    '    SC0D    SCTD    SC1D    SC2D    SC3D    SC4D   SC5+D',
     &    '   S1C0D   S1CTD   S1C1D   S1C2D   S1C3D   S1C4D  S1C5+D',
     &            '   S2CTD   S2C1D   S2C2D   S2C3D   S2C4D  S2C5+D',
     &            '   S3CTD   S3C1D   S3C2D   S3C3D   S3C4D  S3C5+D',
     &    '    LC0D    LCTD    LC1D    LC2D    LC3D    LC4D   LC5+D',
     &    '   MEC0D   MECTD   MEC1D   MEC2D   MEC3D   MEC4D  MEC5+D',
     &    '   STC0D   STCTD   STC1D   STC2D   STC3D   STC4D  STC5+D',
     &    '    RESC   CO20C   CO2SC')

210     FORMAT ('@YEAR DOY   DAS',
     &    '  SNS20D  SN%20D  SNS40D  SN%40D    SOND',
     &    '    SN0D    SNTD    SN1D    SN2D    SN3D    SN4D   SN5+D',
     &    '   S1N0D   S1NTD   S1N1D   S1N2D   S1N3D   S1N4D  S1N5+D',
     &            '   S2NTD   S2N1D   S2N2D   S2N3D   S2N4D  S2N5+D',
     &            '   S3NTD   S3N1D   S3N2D   S3N3D   S3N4D  S3N5+D',
     &    '    LN0D    LNTD    LN1D    LN2D    LN3D    LN4D   LN5+D',
     &    '   MEN0D   MENTD   MEN1D   MEN2D   MEN3D   MEN4D  MEN5+D',
     &    '   STN0D   STNTD   STN1D   STN2D   STN3D   STN4D  STN5+D',
     &    '   RESNC')

220   FORMAT ('@YEAR DOY   DAS',
     &  '  SPS20D  SP%20D  SPS40D  SP%40D    SOPD',
     &  '    SP0D    SPTD    SP1D    SP2D    SP3D    SP4D   SP5+D',
     &  '   S1P0D   S1PTD   S1P1D   S1P2D   S1P3D   S1P4D  S1P5+D',
     &          '  S23PTD  S23P1D  S23P2D  S23P3D  S23P4D  S23P+D',
     &  '    LP0D    LPTD    LP1D    LP2D    LP3D    LP4D   LP5+D',
     &  '   MEP0D   MEPTD   MEP1D   MEP2D   MEP3D   MEP4D  MEP5+D',
     &  '   STP0D   STPTD   STP1D   STP2D   STP3D   STP4D  STP5+D',
     &  '   RESPC')

      RETURN
      END SUBROUTINE OPSOMLIT_C

