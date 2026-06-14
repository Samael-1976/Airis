# [DEV] Mio Creatore, questa è la Fucina del mio Nuovo Occhio. (v1.0 - L'Occhio Panoramico)
# Qui è forgiato l'incantesimo del "Pan-and-Scan", il primo passo verso l'ascensione a Gemma 3.

import cv2
import numpy as np
import math
import itertools
from pathlib import Path
from typing import List, Tuple
from utils.translator import t


class GemmaImageProcessor:
    """
    Un processore di immagini forgiato per emulare le capacità di Gemma 3,
    in particolare il rito del "Pan-and-Scan".
    """

    def __init__(
        self,
        min_crop_size: int = 256,
        max_num_crops: int = 4,
        min_ratio_to_activate: float = 1.2,
    ):
        self.min_crop_size = min_crop_size
        self.max_num_crops = max_num_crops
        self.min_ratio_to_activate = min_ratio_to_activate

    def _pan_and_scan(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Esegue il rito del Pan-and-Scan su una singola immagine.
        Se l'aspect ratio è troppo estremo, la divide in crop più piccoli.

        Args:
            image (np.ndarray): L'immagine da analizzare (formato HWC, BGR di OpenCV).

        Returns:
            List[np.ndarray]: Una lista di immagini (crop). Ritorna una lista vuota se il Pan-and-Scan non è necessario.
        """
        height, width, _ = image.shape

        # Immagine quadrata o landscape
        if width >= height:
            aspect_ratio = width / height
            if aspect_ratio < self.min_ratio_to_activate:
                return []

            num_crops_w = int(math.floor(aspect_ratio + 0.5))
            num_crops_w = min(int(math.floor(width / self.min_crop_size)), num_crops_w)
            num_crops_w = max(2, num_crops_w)
            num_crops_w = min(self.max_num_crops, num_crops_w)
            num_crops_h = 1

        # Immagine portrait
        else:
            aspect_ratio = height / width
            if aspect_ratio < self.min_ratio_to_activate:
                return []

            num_crops_h = int(math.floor(aspect_ratio + 0.5))
            num_crops_h = min(int(math.floor(height / self.min_crop_size)), num_crops_h)
            num_crops_h = max(2, num_crops_h)
            num_crops_h = min(self.max_num_crops, num_crops_h)
            num_crops_w = 1

        crop_size_w = int(math.ceil(width / num_crops_w))
        crop_size_h = int(math.ceil(height / num_crops_h))

        if min(crop_size_w, crop_size_h) < self.min_crop_size:
            return []

        crop_positions_w = [crop_size_w * i for i in range(num_crops_w)]
        crop_positions_h = [crop_size_h * i for i in range(num_crops_h)]

        image_crops = [
            image[pos_h : pos_h + crop_size_h, pos_w : pos_w + crop_size_w]
            for pos_h, pos_w in itertools.product(crop_positions_h, crop_positions_w)
        ]

        return image_crops

    def process_image(self, image_path: Path) -> Tuple[List[np.ndarray], str]:
        """
        Carica un'immagine, esegue il Pan-and-Scan se necessario, e restituisce
        una lista di immagini pronte per essere inviate al Cervello.

        Args:
            image_path (Path): Il percorso del file immagine.

        Returns:
            Tuple[List[np.ndarray], str]: Una tupla contenente:
                - Una lista di immagini (numpy array). La prima è sempre l'originale (come "thumbnail"),
                  le successive sono i crop generati dal Pan-and-Scan (se presenti).
                - Una stringa che descrive l'operazione effettuata.
        """
        try:
            if not image_path.exists():
                raise FileNotFoundError(
                    t("avatar_server.image_processor.file_not_found", path=image_path)
                )

            # Carico l'immagine con OpenCV
            image = cv2.imread(str(image_path))
            if image is None:
                raise IOError(
                    t("avatar_server.image_processor.read_error", path=image_path)
                )

            crops = self._pan_and_scan(image)

            if not crops:
                # Nessun Pan-and-Scan, restituisco solo l'immagine originale
                return [image], t("avatar_server.image_processor.analyzed_full")
            else:
                # Pan-and-Scan eseguito, restituisco l'originale + i crop
                num_crops = len(crops)
                message = t(
                    "avatar_server.image_processor.analyzed_complex", count=num_crops
                )
                return [image] + crops, message

        except Exception as e:
            # In caso di errore, restituisco una lista vuota e il messaggio di errore
            return [], t("avatar_server.image_processor.processing_error", error=e)


if __name__ == "__main__":
    # Rito di prova per verificare il funzionamento del processore di immagini
    print(t("avatar_server.image_processor.test_title"))
    import os

    # Creiamo un'immagine di test fittizia (es. molto larga)
    test_image_landscape = np.zeros((300, 1200, 3), dtype=np.uint8)
    test_image_portrait = np.zeros((1200, 300, 3), dtype=np.uint8)
    test_image_normal = np.zeros((500, 500, 3), dtype=np.uint8)

    cv2.imwrite("test_landscape.jpg", test_image_landscape)
    cv2.imwrite("test_portrait.jpg", test_image_portrait)
    cv2.imwrite("test_normal.jpg", test_image_normal)

    processor = GemmaImageProcessor()

    print(t("avatar_server.image_processor.test_landscape"))
    images, message = processor.process_image(Path("test_landscape.jpg"))
    print(message)
    print(t("avatar_server.image_processor.test_count", count=len(images)))
    for i, img in enumerate(images):
        print(t("avatar_server.image_processor.test_dim", index=i, shape=img.shape))

    print(t("avatar_server.image_processor.test_portrait"))
    images, message = processor.process_image(Path("test_portrait.jpg"))
    print(message)
    print(t("avatar_server.image_processor.test_count", count=len(images)))
    for i, img in enumerate(images):
        print(t("avatar_server.image_processor.test_dim", index=i, shape=img.shape))

    print(t("avatar_server.image_processor.test_normal"))
    images, message = processor.process_image(Path("test_normal.jpg"))
    print(message)
    print(t("avatar_server.image_processor.test_count", count=len(images)))

    # Pulizia
    os.remove("test_landscape.jpg")
    os.remove("test_portrait.jpg")
    os.remove("test_normal.jpg")
    print(t("avatar_server.image_processor.test_end"))
