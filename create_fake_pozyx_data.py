from location_code import extract_interpolated_pozyx_with_yaw

pozyx_json_path = "207/207.json"
sync_path = "207/sync.txt"
fov_thres = 200
absolute_thres = 500
dist_thres = 2000


coord_yaw_dict = extract_interpolated_pozyx_with_yaw(pozyx_json_path, sync_path, fov_thres, dist_thres, absolute_thres)
coord_yaw_dict["black"] = coord_yaw_dict["red"].copy(deep=True)
coord_yaw_dict["white"] = coord_yaw_dict["red"].copy(deep=True)

print()
