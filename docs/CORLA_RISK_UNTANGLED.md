# Input on untangling the CORLA data files:

1. the following files are sufficient for calculating the uniform audit risks:

     val tabulateCountyFile = "2024/general/tabulateCounty.csv"
     val contestRoundFile =   "2024/general/round1/contest.csv"
     val mvrComparisonFile =  "2024/general/round3/contestComparison.csv"
     
 2. generalCanonicalFile can be used for the canonical contestName, choiceNames, and counties (with 3 modifications)

 generalCanonicalFile = "2024/general/2024GeneralCanonicalList.csv"
    with following contests added:
      CanonicalContest("Bannock Ballot Issue 6A", choices = listOf("Yes", "No"), counties=listOf("Douglas")
      CanonicalContest("Spring Canyon Ballot Issue 6B", choices = listOf("Yes", "No"), counties=listOf("Douglas")
    and the following contest removed:
      CanonicalContest("La Plata County Surveyor", comment="There are no candidates for this office")

    the names in tabulateCountyFile, contestRoundFile, mvrComparisonFile agree with generalCanonicalFile
    tabulateCountyFile, contestRoundFile have every name in generalCanonicalFile
    mvrComparisonFile is missing 58 contests that are in generalCanonicalFile
