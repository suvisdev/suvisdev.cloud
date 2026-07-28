# Neo4j 그래프 DB 확인 하네스

## 그래프 데이터 모델

그래프 데이터는 노드(node), 라벨(label), 관계(relationship), 속성(property)로
정의되며, 노드와 관계는 그래프를 구성하는 기본 단위다.

- **노드(Node)**: 그래프에서 동그라미로 표현되는 각각의 개체. 노드를 통해
  엔티티를 식별할 수 있다.
- **라벨(Label)**: 노드에 붙는 `Person`, `Book` 같은 이름 — 노드의 분류에
  사용된다. 예를 들어 `Person` 라벨을 가진 두 개의 노드와 `Book` 라벨을
  가진 한 개의 노드로 그래프가 구성될 수 있다.
- **관계(Relationship)**: 두 노드를 연결하며, 화살표로 방향을 표현할 수도
  있다. 두 사람(`Person`)이 책(`Book`)을 "읽었다"는 관계는 `:HAS_READ`로,
  두 사람이 "친구다"라는 관계는 `:IS_FRIENDS_WITH`로 연결한다.
- **속성(Property)**: 노드·관계에 설명을 추가하는 값. `Person` 노드는
  `name`, `age` 속성을 가질 수 있고, `:HAS_READ` 관계에는 읽은 날짜를
  담는 `on` 속성을 추가할 수 있다.

## 현재 상태

- `.env`에 `NEO4J_PASSWORD`만 정의돼 있다. `NEO4J_URI`, `NEO4J_USER`는
  아직 없음 — 인스턴스가 뜨면 `apps/ontology/_docs/star-craft-pipeline.md`
  컨벤션대로 추가한다.
- docker-compose에 neo4j 서비스가 아직 없다. 로컬(7474/7687), EC2 모두
  실행 중인 인스턴스 없음 (2026-07-27 기준 확인).
- `neo4j-graphrag`(→ `neo4j` 드라이버 포함) 패키지는 `~/.venv`에 설치돼
  있다 (`requirements.txt`에 `neo4j-graphrag==1.18.0`).

아래는 인스턴스가 준비된 뒤 연결·데이터를 확인하는 방법이다.

## 필요한 환경변수

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<.env의 NEO4J_PASSWORD>
```

## 1. Python 드라이버로 확인

```python
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
auth = ("neo4j", "<NEO4J_PASSWORD>")

with GraphDatabase.driver(uri, auth=auth) as driver:
    driver.verify_connectivity()  # 연결 실패 시 여기서 예외 발생
    print("Neo4j 연결 성공")

    with driver.session() as session:
        # 전체 노드 수
        count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
        print(f"노드 수: {count}")

        # 존재하는 라벨 목록
        labels = [r["label"] for r in session.run("CALL db.labels() YIELD label RETURN label")]
        print(f"라벨: {labels}")

        # 존재하는 관계 타입 목록
        rel_types = [
            r["relationshipType"]
            for r in session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        ]
        print(f"관계 타입: {rel_types}")
```

## 2. cypher-shell로 확인 (컨테이너로 띄운 경우)

```bash
docker exec -it <neo4j-container-name> cypher-shell -u neo4j -p "$NEO4J_PASSWORD"
```

```cypher
// 연결 확인
RETURN 1 AS ok;

// 노드 수
MATCH (n) RETURN count(n) AS node_count;

// 라벨별 노드 수
MATCH (n) RETURN labels(n) AS labels, count(*) AS count;

// 관계 타입별 개수
MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS count;
```

## 3. 브라우저 UI로 확인

`http://localhost:7474` 접속 → `neo4j` / `NEO4J_PASSWORD`로 로그인 →
좌측 데이터베이스 정보 패널에서 노드·관계 수, 라벨 목록을 바로 확인할 수
있다.

## 예시 데이터 (검증용)

```cypher
CREATE (alice:Person {name: "Alice", age: 30})
CREATE (bob:Person {name: "Bob", age: 32})
CREATE (book:Book {title: "The Great Gatsby"})

CREATE (alice)-[:HAS_READ {on: date("2026-05-01")}]->(book)
CREATE (bob)-[:HAS_READ {on: date("2026-06-12")}]->(book)
CREATE (alice)-[:IS_FRIENDS_WITH]->(bob)
```

위 데이터를 넣은 뒤 `MATCH (n) RETURN count(n)`이 3, `db.labels()`가
`["Person", "Book"]`, `db.relationshipTypes()`가
`["HAS_READ", "IS_FRIENDS_WITH"]`를 반환하면 연결·쓰기·조회가 모두
정상이라는 뜻이다.
