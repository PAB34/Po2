import { useMemo, useState, type ReactNode } from "react";

type SortValue = string | number | null | undefined;
type DataTableColumn<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  // Rend l'entête cliquable pour trier (asc → desc → aucun). Absent = colonne non triable.
  sortValue?: (row: T) => SortValue;
};
type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
};

type SortState = { key: string; dir: "asc" | "desc" };

function compare(a: SortValue, b: SortValue): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1; // nulls en dernier
  if (b == null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "fr", { numeric: true });
}

export function DataTable<T>({ columns, rows, getRowKey, onRowClick }: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState | null>(null);

  const sortedRows = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue) return rows;
    const sortValue = col.sortValue;
    return [...rows].sort((a, b) => {
      const cmp = compare(sortValue(a), sortValue(b));
      return sort.dir === "asc" ? cmp : -cmp;
    });
  }, [rows, sort, columns]);

  function toggleSort(key: string) {
    setSort((prev) =>
      prev?.key !== key ? { key, dir: "asc" } : prev.dir === "asc" ? { key, dir: "desc" } : null,
    );
  }

  return (
    <div className="po2-table-wrap">
      <table className="po2-table">
        <thead>
          <tr>
            {columns.map((column) => {
              const sortable = typeof column.sortValue === "function";
              const active = sort?.key === column.key;
              return (
                <th
                  key={column.key}
                  onClick={sortable ? () => toggleSort(column.key) : undefined}
                  className={sortable ? "po2-table__th--sortable" : undefined}
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                  style={sortable ? { cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" } : undefined}
                >
                  {column.header}
                  {sortable ? (
                    <span style={{ opacity: active ? 0.9 : 0.35 }}> {active ? (sort!.dir === "asc" ? "▲" : "▼") : "⇅"}</span>
                  ) : null}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr
              key={getRowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={onRowClick ? "po2-table__row--clickable" : undefined}
            >
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
