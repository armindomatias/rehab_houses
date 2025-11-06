interface HouseCardProps {
  title?: string;
  price?: string;
  location?: string;
  onClick?: () => void;
}

export default function HouseCard({ title, price, location, onClick }: HouseCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
    >
      {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
      {price && <p className="text-gray-600 mb-2">{price}</p>}
      {location && <p className="text-sm text-gray-500">{location}</p>}
    </div>
  );
}

