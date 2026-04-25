from rag_core import INDEX_PATH, build_index


def main() -> None:
    index = build_index()
    print(f"Indexed {index['chunk_count']} chunks")
    print(f"Index: {INDEX_PATH}")


if __name__ == "__main__":
    main()
