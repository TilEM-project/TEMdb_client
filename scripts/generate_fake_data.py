import asyncio
import random
from datetime import datetime, timedelta
from temdb_client import (
    create_client,
    TEMdbClientError,
    NotFoundError,
    AsyncTEMdbClient,
)
import argparse

# # Constants for tile generation
# TILE_SIZE = 21512  # nm
# OVERLAP = 0.06  # 6% overlap
# STAGE_SIZE = 1_000_000  # nm


def get_parser():
    parser = argparse.ArgumentParser(
        description="A tool for generating fake data for TEMdb."
    )

    # Server configuration
    parser.add_argument("url", type=str, help="The base URL of the TEMdb server.")

    # Physical parameters
    parser.add_argument(
        "--tile-size", type=int, default=21512, help="Tile size in nm (default: 21512)"
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=0.06,
        help="Tile overlap as fraction (default: 0.06)",
    )
    parser.add_argument(
        "--stage-size",
        type=int,
        default=100000,
        help="Stage size in nm (default: 100000)",
    )

    # Data volume parameters
    parser.add_argument(
        "--num-blocks",
        type=int,
        default=2,
        help="Number of blocks to create (default: 2)",
    )
    parser.add_argument(
        "--cutting-sessions-per-block",
        type=int,
        default=1,
        help="Number of cutting sessions per block (default: 1)",
    )
    parser.add_argument(
        "--sections-per-session",
        type=int,
        default=10,
        help="Number of sections per cutting session (default: 10)",
    )
    parser.add_argument(
        "--rois-per-imaging-session",
        type=int,
        default=5,
        help="Number of ROIs per imaging session (default: 5)",
    )

    return parser


def generate_jittered_roi(base_x, base_y, base_width, base_height, jitter=5):
    return {
        "aperture_centroid": [
            base_x + random.uniform(-jitter, jitter),
            base_y + random.uniform(-jitter, jitter),
        ],
        "aperture_width_height": [
            base_width + random.uniform(-jitter, jitter),
            base_height + random.uniform(-jitter, jitter),
        ],
    }


def calculate_stage_position(row, col, tile_size, overlap):
    effective_tile_size = tile_size * (1 - overlap)
    x = col * effective_tile_size
    y = row * effective_tile_size
    jitter_x = random.uniform(-tile_size * 0.01, tile_size * 0.01)
    jitter_y = random.uniform(-tile_size * 0.01, tile_size * 0.01)
    return {"x": x + jitter_x, "y": y + jitter_y}


def generate_focus_score(base_score=21, variation=0.5):
    return max(0, min(24, random.gauss(base_score, variation)))


def generate_matcher_data(row, col):
    return {
        "row": row,
        "col": col,
        "dX": random.uniform(-5, 5),
        "dY": random.uniform(-5, 5),
        "dXsd": random.uniform(0, 2),
        "dYsd": random.uniform(0, 2),
        "distance": random.uniform(0, 10),
        "rotation": random.uniform(-0.1, 0.1),
        "match_quality": random.uniform(0.5, 1),
        "position": row * 10 + col,
        "pX": [random.uniform(0, 100) for _ in range(4)],
        "pY": [random.uniform(0, 100) for _ in range(4)],
        "qX": [random.uniform(0, 100) for _ in range(4)],
        "qY": [random.uniform(0, 100) for _ in range(4)],
    }


async def create_specimen(client):
    specimen_data = {
        "specimen_id": f"SPEC{random.randint(1000, 9999)}",
        "description": f"Test specimen {random.randint(1, 100)}",
        "created_at": datetime.now().isoformat(),
    }
    specimen = await client.specimen.create(specimen_data)
    print(f"Created specimen: {specimen['specimen_id']}")
    return specimen


async def create_blocks(client: AsyncTEMdbClient, specimen, num_blocks):
    blocks = []
    for i in range(num_blocks):
        block_data = {
            "block_id": f"BLK_{specimen['specimen_id']}_{i+1:03d}",
            "specimen_id": specimen["specimen_id"],
            "microCT_info": {"resolution": random.uniform(0.5, 2.0)},
        }
        block = await client.block.create(block_data)
        blocks.append(block)
        print(f"Created block: {block['block_id']}")
    return blocks


async def create_cutting_session(client: AsyncTEMdbClient, block, session_number):
    media_id = f"TAPE{block['block_id']}{session_number}"
    cutting_session_data = {
        "cutting_session_id": f"CUT{block['block_id']}{session_number}",
        "block_id": block["block_id"],
        "start_time": (datetime.now() + timedelta(days=session_number)).isoformat(),
        "operator": f"Operator {random.randint(1, 5)}",
        "sectioning_device": "Ultra Microtome 3000",
        "media_type": "tape",
        "media_id": media_id,
    }
    cutting_session = await client.cutting_session.create(cutting_session_data)
    print(f"Created cutting session: {cutting_session['cutting_session_id']}")
    return cutting_session, media_id


async def create_section(
    client: AsyncTEMdbClient, cutting_session, section_number, media_id
):
    section_data = {
        "section_id": f"SEC{cutting_session['cutting_session_id']}{section_number:03d}",
        "section_number": section_number,
        "cutting_session_id": cutting_session["cutting_session_id"],
        "media_type": "tape",
        "media_id": media_id,
        "relative_position": section_number,
    }
    section = await client.section.create(section_data)
    print(f"Created section: {section['section_id']}")
    return section


async def create_roi(
    client: AsyncTEMdbClient, section, roi_id, jittered_roi, block, specimen
):
    roi_data = {
        "roi_id": roi_id,
        "section_number": section["section_number"],
        "aperture_width_height": jittered_roi["aperture_width_height"],
        "aperture_centroid": jittered_roi["aperture_centroid"],
        "specimen_id": specimen["_id"],
        "block_id": block["_id"],
    }
    roi = await client.roi.create(roi_data)
    print(f"Created ROI: {roi['roi_id']} for section {section['section_id']}")
    return roi


async def create_imaging_session(
    client: AsyncTEMdbClient, specimen, block, media_id, session_number
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    random_id = "".join(random.choices("0123456789", k=6))

    session_id = (
        f"IMS_{specimen['specimen_id']}_{session_number:03d}_{timestamp}_{random_id}"
    )

    print(f"Creating imaging session: {session_id}")

    imaging_session_data = {
        "session_id": session_id,
        "specimen_id": specimen["specimen_id"],
        "block_id": block["block_id"],
        "media_type": "tape",
        "media_id": media_id,
        "start_time": datetime.now().isoformat(),
    }
    imaging_session = await client.imaging_session.create(imaging_session_data)
    print(f"Created imaging session: {imaging_session['session_id']}")
    return imaging_session


async def create_acquisition(client: AsyncTEMdbClient, imaging_session, roi, args):
    acquisition_data = {
        "acquisition_id": f"ACQ{imaging_session['session_id']}{roi['roi_id']}",
        "roi_id": roi["roi_id"],
        "imaging_session_id": imaging_session["session_id"],
        "montage_id": f"MONTAGE{imaging_session['session_id']}{roi['roi_id']}",
        "hardware_settings": {
            "scope_id": "T1",
            "camera_model": "MX1276",
            "camera_serial": "1234",
            "bit_depth": 10,
            "media_type": "tape",
        },
        "acquisition_settings": {
            "magnification": 2000,
            "spot_size": 5,
            "exposure_time": 120,
            "tile_size": [args.tile_size, args.tile_size],
            "tile_overlap": args.overlap,
        },
        "calibration_info": {
            "pixel_size": 4.0,
            "stig_angle": 0,
            "lens_model": None,
        },
        "status": "planned",
        "tilt_angle": 0,
        "lens_correction": True,
        "start_time": datetime.now().isoformat(),
    }

    acquisition = await client.acquisition.create(acquisition_data)
    print(f"Created acquisition: {acquisition['acquisition_id']}")
    return acquisition


async def create_tiles(client: AsyncTEMdbClient, acquisition, media_id, args):
    tiles = []
    base_focus_score = random.uniform(20.5, 21.5)
    tiles_per_side = int(args.stage_size / (args.tile_size * (1 - args.overlap)))
    total_tiles = tiles_per_side * tiles_per_side

    for k in range(total_tiles):
        row, col = k // tiles_per_side, k % tiles_per_side
        focus_score = generate_focus_score(base_focus_score)
        stage_position = calculate_stage_position(
            row, col, args.tile_size, args.overlap
        )

        tile_data = {
            "tile_id": f"TILE{acquisition['acquisition_id']}{k+1:05d}",
            "acquisition_id": acquisition["acquisition_id"],
            "stage_position": stage_position,
            "raster_position": {"row": row, "col": col},
            "focus_score": focus_score,
            "min_value": random.randint(0, 20),
            "max_value": random.randint(200, 255),
            "mean_value": random.randint(100, 200),
            "std_value": random.uniform(10, 40),
            "image_path": f"/path/to/images/{media_id}/{acquisition['acquisition_id']}/{k+1:05d}.tif",
            "matcher": [
                generate_matcher_data(row, col),
                generate_matcher_data(row, col + 1),
                generate_matcher_data(row + 1, col),
                generate_matcher_data(row + 1, col + 1),
            ],
            "raster_index": k + 1,
        }

        created_tile = await client.acquisition.add_tile(
            acquisition["acquisition_id"], tile_data
        )
        tiles.append(created_tile)
        print(f"Created tile: {created_tile['tile_id']}")

    return tiles


async def generate_data(client: AsyncTEMdbClient, args):
    try:
        specimen = await create_specimen(client)
        blocks = await create_blocks(client, specimen, args.num_blocks)
        total_imaging_sessions = 0
        total_rois = 0

        # Process each block completely before moving to the next
        for block in blocks:
            session_counters = {}
            block_rois = []

            # Create all ROIs for this block
            for j in range(args.cutting_sessions_per_block):
                cutting_session, media_id = await create_cutting_session(
                    client, block, j + 1
                )

                if media_id not in session_counters:
                    session_counters[media_id] = 0

                base_x, base_y = random.randint(50, 150), random.randint(50, 150)
                base_width, base_height = random.randint(100, 200), random.randint(
                    100, 200
                )

                for k in range(args.sections_per_session):
                    section = await create_section(
                        client, cutting_session, k + 1, media_id
                    )
                    jittered_roi = generate_jittered_roi(
                        base_x, base_y, base_width, base_height
                    )
                    roi = await create_roi(
                        client,
                        section,
                        int(f"{j+1}{k+1:03d}"),
                        jittered_roi,
                        block,
                        specimen,
                    )
                    block_rois.append((roi, media_id))
            rois_by_media = {}
            for roi, media_id in block_rois:
                if media_id not in rois_by_media:
                    rois_by_media[media_id] = []
                rois_by_media[media_id].append(roi)

            for media_id, media_rois in rois_by_media.items():
                num_sessions = len(media_rois) // args.rois_per_imaging_session
                print(f"\nProcessing block {block['block_id']} media {media_id}:")
                print(f"- Created {len(media_rois)} ROIs")
                print(f"- Creating {num_sessions} imaging sessions")

                for i in range(num_sessions):
                    session_counters[media_id] += 1
                    print(f"  Creating imaging session {session_counters[media_id]}")
                    imaging_session = await create_imaging_session(
                        client, specimen, block, media_id, session_counters[media_id]
                    )

                    start_idx = i * args.rois_per_imaging_session
                    end_idx = start_idx + args.rois_per_imaging_session
                    session_rois = media_rois[start_idx:end_idx]

                    for roi in session_rois:
                        await client.imaging_session.add_rois(
                            imaging_session["session_id"], roi["roi_id"]
                        )
                        print(
                            f"  Added ROI {roi['roi_id']} to imaging session {imaging_session['session_id']}"
                        )

                        acquisition = await create_acquisition(
                            client, imaging_session, roi, args
                        )
                        await create_tiles(client, acquisition, media_id, args)

                    total_imaging_sessions += 1

            total_rois += len(block_rois)

        print("\nData generation summary:")
        print(f"Created {len(blocks)} blocks")
        print(f"Created {total_rois} ROIs")
        print(f"Created {total_imaging_sessions} imaging sessions")
        tiles_per_acquisition = int(
            (args.stage_size / (args.tile_size * (1 - args.overlap))) ** 2
        )
        total_tiles = (
            total_imaging_sessions
            * args.rois_per_imaging_session
            * tiles_per_acquisition
        )
        print(
            f"Created {total_tiles} total tiles ({tiles_per_acquisition} tiles per acquisition)"
        )

    except TEMdbClientError as e:
        print(f"An error occurred: {e}")
    except NotFoundError as e:
        print(f"Resource not found: {e}")


async def main():
    parser = get_parser()
    args = parser.parse_args()

    async with create_client(args.url, async_mode=True) as client:
        await generate_data(client, args)


if __name__ == "__main__":
    asyncio.run(main())
