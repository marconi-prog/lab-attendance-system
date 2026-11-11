import { useWindowDimensions } from 'react-native';

export function useResponsive() {
  const { width, height } = useWindowDimensions();
  return { width, height, isWide: width >= 900, isPhone: width < 600 };
}
