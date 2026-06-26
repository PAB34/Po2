import type { ReactNode } from "react";
type DataTableColumn<T> = { key: string; header: string; render: (row: T) => ReactNode; };
type DataTableProps<T> = { columns: DataTableColumn<T>[]; rows: T[]; getRowKey: (row: T) => string | number; onRowClick?: (row: T) => void; };

export function DataTable<T>({ columns, rows, getRowKey, onRowClick }: DataTableProps<T>) {
  return <div className="po2-table-wrap"><table className="po2-table"><thead><tr>{columns.map((column) => <th key={column.key}>{column.header}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={getRowKey(row)} onClick={onRowClick ? () => onRowClick(row) : undefined} className={onRowClick ? "po2-table__row--clickable" : undefined}>{columns.map((column) => <td key={column.key}>{column.render(row)}</td>)}</tr>)}</tbody></table></div>;
}
