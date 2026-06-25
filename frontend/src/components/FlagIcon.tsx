import { getFlagCode } from '../utils/flags';

interface FlagIconProps {
  countryCode?: string | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_STYLES: Record<string, string> = {
  sm: 'w-5 h-4',
  md: 'w-7 h-5',
  lg: 'w-9 h-7',
};

export default function FlagIcon({ countryCode, size = 'lg', className = '' }: FlagIconProps) {
  const iso2 = getFlagCode(countryCode);
  const sizeClass = SIZE_STYLES[size];

  if (!iso2) {
    return (
      <span
        className={`inline-block rounded-sm bg-slate-700 ${sizeClass} ${className}`}
        aria-hidden="true"
      />
    );
  }

  return (
    <span
      className={`fi fi-${iso2} inline-block rounded-sm ${sizeClass} ${className}`}
      aria-hidden="true"
    />
  );
}
