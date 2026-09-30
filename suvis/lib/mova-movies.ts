import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"

type MovaCastMember = {
  name: string
  role: string
  photo: string
  /** 실 API 전용 — 배우 상세(/mova/actors/{id}) 연동 키. 목업 데이터는 채우지 않는다. */
  actorId?: number
}

export type MovaComment = {
  id: string
  user: string
  rating: number
  text: string
  likes: number
  commentCount: number
  spoilerSpans?: { start: number; end: number; text: string }[]
  sentimentLabel?: string | null
  sentimentScore?: number | null
  newsSourceCount?: number | null
  newsSources?: { title: string; url: string; source: string }[] | null
}

export type MovaMovie = {
  /** 백엔드 `movies.id` — API 리뷰 연동 시 필요 */
  movieDbId?: number
  id: string
  title: string
  year: string
  genres: string[]
  country: string
  ageRating: string
  rankBadge?: string
  platform?: "netflix" | "disney"
  /** 실 API 전용 — 링크가 있는 모든 플랫폼(복수). 목업 데이터는 채우지 않는다. */
  platforms?: { provider: string; url: string | null }[]
  /** 실 API 전용 — YouTube video key. 목업 데이터는 채우지 않는다. */
  trailerKey?: string | null
  poster: string
  backdrop: string
  rating: number
  ratingCount: number
  rank: number
  badge?: "NEW" | "AD"
  synopsis: string
  /** 0.5 ~ 5.0 별점 분포 (10칸) */
  ratingDistribution: number[]
  cast: MovaCastMember[]
  comments: MovaComment[]
  gallery: string[]
}

const TMDB_IMG = (path: string, size: "w200" | "w500" | "w1280" = "w500") =>
  `https://image.tmdb.org/t/p/${size}${path}`

const MOVA_MOVIES: MovaMovie[] = [
  {
    id: "wonderfuls",
    title: "원더풀스",
    year: "2026",
    genres: ["코미디", "액션", "모험", "드라마", "TV드라마"],
    country: "한국",
    ageRating: "15세",
    rankBadge: "한국 시리즈 인기 순위 1위",
    platform: "netflix",
    poster: "https://images.unsplash.com/photo-1522869635100-9f4d2f0de6f5?w=400&q=80",
    backdrop: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=1400&q=80",
    rating: 3.0,
    ratingCount: 1057,
    rank: 0,
    synopsis:
      "평범한 일상 속에서 벌어지는 기묘한 사건들. 웃음과 긴장이 교차하는 한국형 히어로 코미디 드라마. Mova AI가 추천하는 이번 주 필수 시리즈입니다.",
    ratingDistribution: [12, 28, 145, 312, 198, 156, 98, 52, 34, 22],
    cast: [
      {
        name: "박은빈",
        role: "출연 | 은채니",
        photo: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&q=80",
      },
      {
        name: "차은우",
        role: "출연 | 민준호",
        photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&q=80",
      },
      {
        name: "김해숙",
        role: "출연 | 어머니",
        photo: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&q=80",
      },
      {
        name: "이동휘",
        role: "출연 | 형사",
        photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&q=80",
      },
    ],
    comments: [
      {
        id: "c1",
        user: "필름러버",
        rating: 3.5,
        text: "1화만 봤는데 톤이 가볍고 재밌어요. 끝까지 볼 예정!",
        likes: 24,
        commentCount: 3,
      },
      {
        id: "c2",
        user: "시리즈덕후",
        rating: 2.5,
        text: "기대보다는 평범했지만 배우 케미는 좋습니다.",
        likes: 11,
        commentCount: 1,
      },
      {
        id: "c3",
        user: "OTT탐험가",
        rating: 4.0,
        text: "넷플릭스에서 이런 한국 드라마 나올 때마다 기분 좋음 ㅎㅎ",
        likes: 45,
        commentCount: 8,
      },
      {
        id: "c4",
        user: "밤샘시청",
        rating: 5.0,
        text: "몰아보기 각입니다. OST도 괜찮아요.",
        likes: 67,
        commentCount: 12,
      },
    ],
    gallery: [
      "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&q=80",
      "https://images.unsplash.com/photo-1535016120720-40c646be5580?w=600&q=80",
      "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=600&q=80",
    ],
  },
  {
    id: "interstellar",
    title: "인터스텔라",
    year: "2014",
    genres: ["SF", "드라마", "모험"],
    country: "미국",
    ageRating: "12세",
    platform: "netflix",
    poster: TMDB_IMG("/gEU2QniE6E77NI6lCU6MxlNBvIE.jpg"),
    backdrop: TMDB_IMG("/xu9zaAevzQ5nnrsXN6JcahLnG4i.jpg", "w1280"),
    rating: 4.5,
    ratingCount: 28420,
    rank: 1,
    badge: "NEW",
    synopsis:
      "지구의 종말이 다가온 미래, 인류를 구하기 위해 우주로 떠난 탐사대의 이야기. 시간과 사랑, 중력을 넘나드는 크리스토퍼 놀란의 대표작.",
    ratingDistribution: [45, 120, 380, 920, 2100, 4200, 5800, 6200, 5100, 3555],
    cast: [
      {
        name: "매튜 맥커너히",
        role: "출연 | 쿠퍼",
        photo: TMDB_IMG("/wJiGedOCZhwMx9DezY8uwbNxmAY.jpg", "w200"),
      },
      {
        name: "앤 해서웨이",
        role: "출연 | 브랜드",
        photo: TMDB_IMG("/tLelKoPNiyJCSEfjC5aFy3F8bLH.jpg", "w200"),
      },
      {
        name: "제시카 차스테인",
        role: "출연 | 머프 (성인)",
        photo: TMDB_IMG("/gKTnpBGjOSjGpqwRMKLaLu1gfxd.jpg", "w200"),
      },
      {
        name: "마이클 케인",
        role: "출연 | 브랜드 교수",
        photo: TMDB_IMG("/veWtl4lhrLjnHI3OmDFVcTP1G2o.jpg", "w200"),
      },
    ],
    comments: [
      {
        id: "c1",
        user: "우주덕후",
        rating: 5.0,
        text: "과학과 감성이 완벽하게 섞인 영화. 다시 봐도 울린다.",
        likes: 892,
        commentCount: 56,
      },
      {
        id: "c2",
        user: "sf마니아",
        rating: 4.5,
        text: "블랙홀 표현이 실제 과학자들도 인정했다더라. 비주얼 레전드.",
        likes: 431,
        commentCount: 22,
      },
    ],
    gallery: [
      TMDB_IMG("/xu9zaAevzQ5nnrsXN6JcahLnG4i.jpg", "w1280"),
      TMDB_IMG("/gEU2QniE6E77NI6lCU6MxlNBvIE.jpg", "w1280"),
    ],
  },
  {
    id: "dune-2",
    title: "듄: 파트2",
    year: "2024",
    genres: ["SF", "모험", "드라마"],
    country: "미국",
    ageRating: "12세",
    platform: "netflix",
    poster: TMDB_IMG("/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg"),
    backdrop: TMDB_IMG("/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg", "w1280"),
    rating: 4.3,
    ratingCount: 15230,
    rank: 2,
    synopsis:
      "아라키스 행성에서 펼쳐지는 운명의 전쟁. 폴 아트레이데스의 여정이 절정에 달하는 서사 시네마.",
    ratingDistribution: [30, 80, 250, 600, 1200, 2400, 3200, 2800, 2100, 1570],
    cast: [
      {
        name: "티모시 샬라메",
        role: "출연 | 폴 아트레이데스",
        photo: TMDB_IMG("/BE2sdjpgsa2rNTFa66f7upkaOP.jpg", "w200"),
      },
      {
        name: "젠다야",
        role: "출연 | 채니",
        photo: TMDB_IMG("/mbYQLBFZCLSzAMzqnLXBHMEkBVA.jpg", "w200"),
      },
      {
        name: "오스틴 버틀러",
        role: "출연 | 페이드-로타",
        photo: TMDB_IMG("/2Uy4mODFGfABMSHPiNS3LlYCmHO.jpg", "w200"),
      },
      {
        name: "레베카 퍼거슨",
        role: "출연 | 레이디 제시카",
        photo: TMDB_IMG("/lJloTOheuQSirSLXNA3JHsrMNfH.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [TMDB_IMG("/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg", "w1280")],
  },
  {
    id: "oppenheimer",
    title: "오펜하이머",
    year: "2023",
    genres: ["드라마", "역사", "스릴러"],
    country: "미국",
    ageRating: "15세",
    poster: TMDB_IMG("/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg"),
    backdrop: TMDB_IMG("/fm6KqXpk3M2HVveHwCrBSSBaO0V.jpg", "w1280"),
    rating: 4.2,
    ratingCount: 22100,
    rank: 3,
    badge: "AD",
    synopsis:
      "원자폭탄 개발의 역사적 순간을 그린 전기 영화. 과학자의 윤리와 정치가 맞물리는 3시간의 서사.",
    ratingDistribution: [40, 100, 300, 700, 1500, 3000, 4000, 4500, 3800, 4160],
    cast: [
      {
        name: "킬리언 머피",
        role: "출연 | 로버트 오펜하이머",
        photo: TMDB_IMG("/dm6V24NjjvjMiCtbMkc8Y2WPm2e.jpg", "w200"),
      },
      {
        name: "로버트 다우니 주니어",
        role: "출연 | 루이스 스트라우스",
        photo: TMDB_IMG("/5qHNjhtjMD4YWH3UP0rm4tKwxCL.jpg", "w200"),
      },
      {
        name: "에밀리 블런트",
        role: "출연 | 키티 오펜하이머",
        photo: TMDB_IMG("/2xxopn7AUZi5LNnPvjrM2yXZgWN.jpg", "w200"),
      },
      {
        name: "맷 데이먼",
        role: "출연 | 레슬리 그로브스",
        photo: TMDB_IMG("/5GFbRDHZKlBrfTljOjQqyJ6ZDeO.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "parasite",
    title: "기생충",
    year: "2019",
    genres: ["드라마", "스릴러", "코미디"],
    country: "한국",
    ageRating: "15세",
    platform: "disney",
    poster: TMDB_IMG("/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"),
    backdrop: TMDB_IMG("/TU9NIjwzjoKPwQHoHshkFcQUCG.jpg", "w1280"),
    rating: 4.6,
    ratingCount: 31200,
    rank: 4,
    synopsis:
      "반지하와 고층 아파트, 두 가족의 운명이 얽히며 벌어지는 블랙 코미디 스릴러. 봉준호 감독의 칸 황금종려상·아카데미 4관왕 수상작.",
    ratingDistribution: [20, 50, 150, 400, 900, 2000, 3500, 5000, 8000, 11180],
    cast: [
      {
        name: "송강호",
        role: "출연 | 기택",
        photo: TMDB_IMG("/rPEXD9lFgq2L5i4jFUqFGVJvjMT.jpg", "w200"),
      },
      {
        name: "이선균",
        role: "출연 | 박동익",
        photo: TMDB_IMG("/6VBNeo8XG390AKYx0ALtkb4fYSP.jpg", "w200"),
      },
      {
        name: "최우식",
        role: "출연 | 기우",
        photo: TMDB_IMG("/ym0bOqlM2WZFN3jomqdWQtHt7bV.jpg", "w200"),
      },
      {
        name: "박소담",
        role: "출연 | 기정",
        photo: TMDB_IMG("/3FdBPFBBvFMXEA5TbcAFicOkpDZ.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "blade-runner-2049",
    title: "블레이드 러너 2049",
    year: "2017",
    genres: ["SF", "스릴러"],
    country: "미국",
    ageRating: "15세",
    poster: TMDB_IMG("/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"),
    backdrop: TMDB_IMG("/ilRyazdMfOUPObHuvCrEYGFjJOA.jpg", "w1280"),
    rating: 4.1,
    ratingCount: 9800,
    rank: 5,
    badge: "NEW",
    synopsis:
      "미래 LA, 레플리컨트와 인간의 경계를 탐구하는 시각적 걸작. 드니 빌뇌브 감독의 촬영미학이 빛나는 SF 누아르.",
    ratingDistribution: [25, 70, 200, 500, 900, 1500, 2000, 1800, 1500, 1305],
    cast: [
      {
        name: "라이언 고슬링",
        role: "출연 | K",
        photo: TMDB_IMG("/rMnhn6dGk5nSQlyRXFSwQPSHOoT.jpg", "w200"),
      },
      {
        name: "해리슨 포드",
        role: "출연 | 릭 데커드",
        photo: TMDB_IMG("/7CcoVFTogQgau99ZCMV3KxROi46.jpg", "w200"),
      },
      {
        name: "아나 드 아르마스",
        role: "출연 | 조이",
        photo: TMDB_IMG("/3vxvsmYLNfYOarMOIiPtBcCwylx.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "lalaland",
    title: "라라랜드",
    year: "2016",
    genres: ["로맨스", "뮤지컬", "드라마"],
    country: "미국",
    ageRating: "12세",
    poster: TMDB_IMG("/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg"),
    backdrop: TMDB_IMG("/mSDsSDwaP3E7dEfUPYy208hhbki.jpg", "w1280"),
    rating: 4.0,
    ratingCount: 18500,
    rank: 6,
    synopsis:
      "꿈을 좇는 두 젊은 예술가의 사랑과 선택. LA를 배경으로 한 뮤지컬 로맨스. 아카데미 감독상·촬영상 수상.",
    ratingDistribution: [30, 90, 250, 600, 1100, 2200, 3000, 3500, 4000, 3730],
    cast: [
      {
        name: "라이언 고슬링",
        role: "출연 | 세바스찬",
        photo: TMDB_IMG("/rMnhn6dGk5nSQlyRXFSwQPSHOoT.jpg", "w200"),
      },
      {
        name: "엠마 스톤",
        role: "출연 | 미아",
        photo: TMDB_IMG("/p5sGgBHQsvMCVkk7EoKsTHYTN41.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "matrix",
    title: "매트릭스",
    year: "1999",
    genres: ["SF", "액션"],
    country: "미국",
    ageRating: "15세",
    poster: TMDB_IMG("/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg"),
    backdrop: TMDB_IMG("/fNG7i7RqMErkcqhohV2a6cV1Ehy.jpg", "w1280"),
    rating: 4.4,
    ratingCount: 25600,
    rank: 7,
    synopsis:
      "가상 현실과 진실의 경계. 네오가 선택한 빨간 알약, SF 액션의 교과서. 워쇼스키 자매가 세운 사이버펑크 세계관.",
    ratingDistribution: [35, 95, 280, 650, 1200, 2500, 4000, 5000, 5500, 5340],
    cast: [
      {
        name: "키아누 리브스",
        role: "출연 | 네오",
        photo: TMDB_IMG("/4D0PpNI0kmP58hgrwGC3wCjxhnm.jpg", "w200"),
      },
      {
        name: "로렌스 피시번",
        role: "출연 | 모피어스",
        photo: TMDB_IMG("/8suOhI1NFMpfMuAqGauUMGvkHuI.jpg", "w200"),
      },
      {
        name: "캐리-앤 모스",
        role: "출연 | 트리니티",
        photo: TMDB_IMG("/hG2gTGpPYZLPrpXrXOyDgEVYQGe.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "inception",
    title: "인셉션",
    year: "2010",
    genres: ["SF", "스릴러", "액션"],
    country: "미국",
    ageRating: "12세",
    platform: "netflix",
    poster: TMDB_IMG("/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"),
    backdrop: TMDB_IMG("/s2bT29y0ngXxxu2IA8AOzzXTRhd.jpg", "w1280"),
    rating: 4.5,
    ratingCount: 29800,
    rank: 8,
    synopsis:
      "꿈 속의 꿈, 생각을 훔치는 도둑들의 미션. 레이어마다 펼쳐지는 놀라운 세계. 크리스토퍼 놀란의 오리지널 SF 블록버스터.",
    ratingDistribution: [40, 110, 320, 750, 1400, 2800, 4500, 5500, 6000, 5380],
    cast: [
      {
        name: "레오나르도 디카프리오",
        role: "출연 | 코브",
        photo: TMDB_IMG("/wo2hJpn04vbtmh0B9utCFdsQhxM.jpg", "w200"),
      },
      {
        name: "조셉 고든-레빗",
        role: "출연 | 아서",
        photo: TMDB_IMG("/zSuXCR6xCKIgo9gQqUBFMSvOmUk.jpg", "w200"),
      },
      {
        name: "톰 하디",
        role: "출연 | 임스",
        photo: TMDB_IMG("/d81K0RH8UX7tZj49tZaQhZ9ewH.jpg", "w200"),
      },
      {
        name: "켄 와타나베",
        role: "출연 | 사이토",
        photo: TMDB_IMG("/gJi7hNiJAMiEfI4nFbCmJSi4ZW5.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "dark-knight",
    title: "다크 나이트",
    year: "2008",
    genres: ["액션", "드라마", "스릴러"],
    country: "미국",
    ageRating: "15세",
    platform: "netflix",
    poster: TMDB_IMG("/qJ2tW6WMUDux911r6m7haRef0WH.jpg"),
    backdrop: TMDB_IMG("/hkBaDkMWbLaf8B1lsWsKX7Ew3Xq.jpg", "w1280"),
    rating: 4.7,
    ratingCount: 35200,
    rank: 9,
    synopsis:
      "배트맨과 조커의 대결. 도시와 정의에 대한 냉철한 질문을 던지는 슈퍼히어로 걸작. 히스 레저의 조커는 영화사에 남을 명연기.",
    ratingDistribution: [20, 60, 180, 400, 900, 1800, 3000, 4500, 6000, 8340],
    cast: [
      {
        name: "크리스찬 베일",
        role: "출연 | 배트맨/브루스 웨인",
        photo: TMDB_IMG("/bzlC6HCa3oEp6MQWKpXlCfMuSXD.jpg", "w200"),
      },
      {
        name: "히스 레저",
        role: "출연 | 조커",
        photo: TMDB_IMG("/5Y9HnYYa9jF4NunY9lSgJGjSe8E.jpg", "w200"),
      },
      {
        name: "아론 에크하트",
        role: "출연 | 하비 덴트",
        photo: TMDB_IMG("/rrh0hj3kR0hH51g5n4JFjnmJxhq.jpg", "w200"),
      },
      {
        name: "마이클 케인",
        role: "출연 | 알프레드",
        photo: TMDB_IMG("/veWtl4lhrLjnHI3OmDFVcTP1G2o.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
  {
    id: "squid-game",
    title: "오징어 게임",
    year: "2021",
    genres: ["스릴러", "드라마", "TV드라마"],
    country: "한국",
    ageRating: "19세",
    platform: "netflix",
    poster: TMDB_IMG("/dDlEmu3EZ0Pgg93K2SVNLCjCSvE.jpg"),
    backdrop: TMDB_IMG("/qw3J9cNeLioOLoR68WX7z79aCdK.jpg", "w1280"),
    rating: 4.2,
    ratingCount: 42100,
    rank: 10,
    badge: "NEW",
    synopsis:
      "생존을 위한 치명적인 게임. 전 세계를 사로잡은 한국 오리지널 시리즈. 넷플릭스 역대 최다 시청 기록.",
    ratingDistribution: [50, 120, 350, 800, 1500, 2800, 4000, 5000, 6500, 8980],
    cast: [
      {
        name: "이정재",
        role: "출연 | 성기훈",
        photo: TMDB_IMG("/mcHuuyMFkHCCrSQqeZAJetlEWRL.jpg", "w200"),
      },
      {
        name: "박해수",
        role: "출연 | 조상우",
        photo: TMDB_IMG("/5qj6UlABPYkGbWaVz77qElAGdqS.jpg", "w200"),
      },
      {
        name: "정호연",
        role: "출연 | 강새벽",
        photo: TMDB_IMG("/0f8lEIZmnFRPML3faCYWIBMxNXq.jpg", "w200"),
      },
      {
        name: "오영수",
        role: "출연 | 오일남",
        photo: TMDB_IMG("/gBV17IlyQbNGjtFaEWa7rPKgD8n.jpg", "w200"),
      },
    ],
    comments: [],
    gallery: [],
  },
]

/** slug·한글 제목·canonical id 로 정적 카탈로그 조회 */
export function findMovaMovie(idOrTitle: string): MovaMovie | undefined {
  const key = idOrTitle.trim()
  if (!key) return undefined
  const canonical = resolveMovaCatalogSlug(key)
  return (
    MOVA_MOVIES.find((m) => m.id === canonical || m.id === key) ??
    MOVA_MOVIES.find((m) => m.title === key)
  )
}

export function searchMovaMovies(query: string): MovaMovie[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return MOVA_MOVIES.filter(
    (m) => m.title.toLowerCase().includes(q) || m.genres.some((g) => g.toLowerCase().includes(q))
  ).slice(0, 8)
}

/** 랭킹 섹션용 (rank > 0) */
export const MOVA_RANKING = MOVA_MOVIES.filter((m) => m.rank > 0).sort((a, b) => a.rank - b.rank)
