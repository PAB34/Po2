type SegmentOption<T extends string> = { value: T; label: string; };
type SegmentControlProps<T extends string> = { value: T; options: SegmentOption<T>[]; onChange: (value: T) => void; };

export function SegmentControl<T extends string>({ value, options, onChange }: SegmentControlProps<T>) {
  return <div className="po2-segment-control" role="tablist">{options.map((option) => <button key={option.value} type="button" className={option.value === value ? "po2-segment-control__button--active" : ""} onClick={() => onChange(option.value)}>{option.label}</button>)}</div>;
}
