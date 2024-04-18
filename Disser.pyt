import arcpy
import math

class Toolbox(object):
    def __init__(self):
        self.label =  "Reconstruction of watercourses"
        self.alias  = "Reconstruction_of_watercourses"
        self.tools = [Reconstruction_of_watercourses, Reconstruction_of_watershades] 

class Reconstruction_of_watercourses(object):
    def __init__(self):
        self.label       = "Reconstruction of watercourses"
        self.description = "Reconstruction of watercourses"

    def getParameterInfo(self):
        DEM_input = arcpy.Parameter(
            displayName="Input DEM",
            name="DEM_input",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        input_mask = arcpy.Parameter(
            displayName="Mask",
            name="input_mask",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        
        out_stream_links = arcpy.Parameter(
            displayName="Output Stream",
            name="out_stream_links",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")
        

        parameters = [DEM_input, input_mask, 
                      out_stream_links]
        
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        DEM_input = parameters[0].valueAsText
        input_mask = parameters[1].valueAsText
        out_stream_links = parameters[2].valueAsText

        # Подготовительный этап. Установка параметров среды: экстент, маска, размер ячейки на основе данных с ЦМР
        arcpy.env.overwriteOutput = True
        arcpy.env.extent = DEM_input
        arcpy.env.snapRaster = DEM_input
        arcpy.env.cellSize = DEM_input
        arcpy.env.mask = input_mask
        cell_x = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEX").getOutput(0)
        cell_y = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEY").getOutput(0)
        cell_area = float(cell_x.replace(',','.')) * float(cell_y.replace(',','.'))  

        # Вычисление углов наклона
        arcpy.AddMessage('Reconstruction of watercourses')
        slope_degree = arcpy.sa.Slope(DEM_input, "DEGREE")
        slope_tangent = arcpy.sa.Times(slope_degree, 0.0174533)  

        # Построение тальвегов
        #Этап 1. Заполнение пустот
        DEM_fill = arcpy.sa.Fill(DEM_input)
        # Этап 2. Создание растра направлений стока
        flow_directions = arcpy.sa.FlowDirection(DEM_fill, "NORMAL", 'slope_degree')

        # Этап 3. Растр суммарного потока
        flow_accumulation = arcpy.sa.FlowAccumulation(flow_directions)

        #Этап 4. Вычисление порогового значения
        CEI = flow_accumulation * cell_area * slope_tangent
        initials = arcpy.sa.Con(CEI > 800, 1)

        #Этап 5. Определение порядкового номера водотока
        stream_number = arcpy.sa.StreamOrder(initials , flow_directions,"STRAHLER")

        #Этап 5. Реконструкция водотоков
        arcpy.sa.StreamToFeature(stream_number, flow_directions, "stream_links", "NO_SIMPLIFY")

        #Этап 6. Объединение водотоков одного порядка
        arcpy.Dissolve_management('stream_links', "stream_dissolve", ["grid_code"], "", "SINGLE_PART", "DISSOLVE_LINES")

        #Этап 7. Разделение водотоков по точка пересечения (разделение v-образных вершин)
        fc_list = []
        i = 1
        arcpy.management.Sort('stream_dissolve', "sort_stream_rang", [["grid_code", "DESCENDING"]])
        values = [i[0] for i in arcpy.da.SearchCursor('sort_stream_rang', "grid_code")]
        max_range = values[1]

        for i in range(max_range):
            rivers_temp = 'rivers_%s_order' % (i+1)
            query = '"grid_code" =' + str(i+2)
            query_i = '"grid_code" =' + str(i+1)
            arcpy.MakeFeatureLayer_management('stream_dissolve', "streams_selection", query)
            arcpy.MakeFeatureLayer_management('stream_dissolve', "streams_selection_i", query_i)
            arcpy.FeatureVerticesToPoints_management('streams_selection', "intersect_point", "BOTH_ENDS")
            arcpy.SplitLineAtPoint_management('streams_selection_i', 'intersect_point', rivers_temp)
            fc_list.append(rivers_temp)
            arcpy.Delete_management('intersect_point')

        arcpy.Merge_management(fc_list, "rivers_output")
        arcpy.Delete_management('streams_selection')
        arcpy.Delete_management('streams_selection_i')
        for fc in fc_list:
            arcpy.Delete_management(fc)

        #Этап 8. Объединение водотоков разного порядка
        out_stream_links = arcpy.Dissolve_management('rivers_output', out_stream_links, "", "", "MULTI_PART", "UNSPLIT_LINES")


class Reconstruction_of_watershades(object):
    def __init__(self):
        self.label       = "Reconstruction of watershades"
        self.description = "Reconstruction of watershades"

    def getParameterInfo(self):
        DEM_input = arcpy.Parameter(
            displayName="Input DEM",
            name="DEM_input",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        input_mask = arcpy.Parameter(
            displayName="Mask",
            name="input_mask",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        select_watercourses = arcpy.Parameter(
            displayName="Select Watercourses",
            name="select_watercourses",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")       
        
        coord_syst = arcpy.Parameter(
            displayName="Coordinate System",
            name="coord_syst",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")

        aval_tranz_zone = arcpy.Parameter(
            displayName="Start zone and Track",
            name="aval_tranz_zone",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        out_stream_links = arcpy.Parameter(
            displayName="Output Stream",
            name="out_stream_links",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        point_output = arcpy.Parameter(
            displayName="point_output",
            name="point_output",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        watershed_output = arcpy.Parameter(
            displayName="watershed_output",
            name="watershed_output",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        

        parameters = [DEM_input, input_mask, select_watercourses, coord_syst, aval_tranz_zone, out_stream_links, point_output, watershed_output

                      ]
        
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        DEM_input = parameters[0].valueAsText
        input_mask = parameters[1].valueAsText
        select_watercourses = parameters[2].valueAsText
        coord_syst = parameters[3].valueAsText

        aval_tranz_zone = parameters[4].valueAsText


        out_stream_links = parameters[5].valueAsText
        point_output = parameters[6].valueAsText
        watershed_output = parameters[7].valueAsText


        # Подготовительный этап. Установка параметров среды: экстент, маска, размер ячейки на основе данных с ЦМР
        arcpy.env.overwriteOutput = True
        arcpy.env.extent = DEM_input
        arcpy.env.snapRaster = DEM_input
        arcpy.env.cellSize = DEM_input
        arcpy.env.mask = input_mask
        cell_x = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEX").getOutput(0)
        cell_y = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEY").getOutput(0)
        cell_area = float(cell_x.replace(',','.')) * float(cell_y.replace(',','.'))  
        cell_p = int(cell_x)

        fc_list = arcpy.ListDatasets()
        for fc in fc_list:
            arcpy.Delete_management(fc)

        # Этап 1. Подготовка данных
        # 1.1. вычисление углов наклона в градусах
        slope_degree = arcpy.sa.Slope(DEM_input, "DEGREE")
        slope_tangent = arcpy.sa.Times(slope_degree, 0.0174533)  
        # 1.2. заполнение "дыр" в ЦМР
        DEM_fill = arcpy.sa.Fill(DEM_input)
        # 1.3. создание растра направлений стока
        flow_directions = arcpy.sa.FlowDirection(DEM_fill, "NORMAL", 'slope_degree')
        # 1.4. объединение участков выбранного водотока в единую линию (dissolve_stream - единая линия)
        arcpy.Dissolve_management(select_watercourses, "dissolve_stream", "", "", "MULTI_PART", "UNSPLIT_LINES")
        # 1.5. извлечение вершин из единой линии и дальнейший их подсчет (необходимо для того, чтобы установить границу возможного агрегирования)
        arcpy.management.FeatureVerticesToPoints('dissolve_stream', "dissolve_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('dissolve_point', DEM_fill, "dissolve_point_rv")
        count_vertices = [i[0] for i in arcpy.da.SearchCursor('dissolve_point_rv', "RASTERVALU")]
        count_vertex = len(count_vertices)
        # 1.6. проверка корректности расположения начала и конца линии (если линия начинается в устье, то разворот)
        razn = count_vertices[0] - count_vertices[-1]
        if razn < 0:
            arcpy.edit.FlipLine('dissolve_stream')
            arcpy.AddMessage('Flip line')
        else:
            arcpy.AddMessage('No flip line')
        # 1.7. создание копии единой линии. Это необходимо для того, чтобы загустить вершины по размеру ячейки ЦМР 
        arcpy.management.Copy('dissolve_stream', "dens_copy")

        #Этап 2. Обрезка водотока
        # 2.1.уплотнение исходной линии в соответствии с размером ячейки (необходимо для извлечения углов наклона из каждой ячейки)
        densify_line = arcpy.edit.Densify('dens_copy', "DISTANCE", cell_x)
        # 2.2 извлечение вершин уплотненной линии и присвоение им значения с растра углов наклона
        arcpy.management.FeatureVerticesToPoints(densify_line, "intersect_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('intersect_point', slope_degree, "out_point") 
        # 2.3. создание списка вершин (в списке хранятся значения углов наклона)
        values_input = [i[0] for i in arcpy.da.SearchCursor('out_point', "RASTERVALU")]
        # 2.4. подготовка к циклу прохода по каждому элементу списка values
        boolval = True
        k = 1
        # 2.5. поиск точки перегиба 
        k = 1
        while True:
            # 2.5.1. создание двух списков из единого (в один записываются индексы всех точек, у которых значение угла наклона больше 20 градсов, в другой - меньше 20)
            points_upper = [values_input.index(i) for i in values_input if i > 20]
            points_below = [values_input.index(i) for i in values_input if i <= 20]
            # 2.5.3. агрегирование исходной ЦМР
            # 2.5.3.1. подготовка к агрегированию
            k = int(k+1)
            cell_agg = cell_p*k
            # 2.5.3.2. удаление переменных, полученных на прошлом этапе итерации (ИСПРАВИТЬ И ДОБАВИТЬ)
            del values_input[:]
            # 2.5.3.3. агрегирование исходной ЦМР 
            DEM_agg = arcpy.sa.Aggregate(DEM_fill, k, "MEAN")
            # 2.5.3.4. построение углов наклона по исходной цмр
            slope_degree_agg = arcpy.sa.Slope(DEM_agg, "DEGREE")
            # 2.5.3.5. копирование изначальной линии и ее загущение во столько же раз во сколько агрегируется ЦМР
            dens_copy_k = 'dens_copy_%s' %k
            arcpy.management.Copy('dissolve_stream', "dens_copy_k")
            arcpy.edit.Densify('dens_copy_k', "DISTANCE", cell_agg)
            # 2.5.3.6. извлечение вершин из уплотненной линии и присвоение им значений с растра углов наклона, полученног по агрегированной ЦМР
            arcpy.management.FeatureVerticesToPoints('dens_copy_k', "intersect_point_agg", "ALL")
            arcpy.sa.ExtractValuesToPoints('intersect_point_agg', slope_degree_agg, "out_point_agg")
            # 2.5.3.7. создание списка для следующей итерации и проверка его длины (количество элементов не должно быть меньше исходного количества точек в линии)
            values_input = [i[0] for i in arcpy.da.SearchCursor('out_point_agg', "RASTERVALU")]
            values_len = int(len(values_input))
            # arcpy.Delete_management(DEM_agg)
            # arcpy.Delete_management(dens_copy_k)
            # arcpy.Delete_management(slope_degree_agg)
            # arcpy.Delete_management('intersect_point_agg')
            
            # 2.5.4. обработка результатов агрегирования
            # 2.5.4.1. в результате агрегирования получаем два массива. В одном ищем первую точку, в другом последнюю
            if values_len == count_vertex:
                query_below = '"OBJECTID" = {0}'.format(points_below[0])
                query_upper = '"OBJECTID" = {0}'.format(points_upper[-1])
                # 2.5.4.2. из выбранных точек создаем временные слои
                arcpy.MakeFeatureLayer_management('out_point_agg', "below_point", query_below)
                arcpy.MakeFeatureLayer_management('out_point_agg', "upper_point", query_upper)
                # 2.5.4.3. объединяем два слоя точек в один
                merge_list = ['below_point', 'upper_point']
                arcpy.Merge_management(merge_list, "point_select_1")
                # 2.5.4.4. по выбранным точкам разрезаем исходную линию
                arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_select_1', "split_lines_3", "5 Meters")  
                # 2.5.4.5. выбор одной линии из трех (той, у которой присутствуют углы наклона и больше 20 градусов и меньше 20) и запись ее на новый слой
                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval = 0
                with arcpy.da.SearchCursor('split_lines_3', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        if (coords_start != split_start and coords_end != split_end):
                            objval = row[1]
                            break
                query_line = '"OBJECTID" = {0}'.format(objval)
                arcpy.MakeFeatureLayer_management('split_lines_3', "select_line", query_line)

                # arcpy.Delete_management('out_point_agg')
                # arcpy.Delete_management('below_point')
                # arcpy.Delete_management('upper_point')
                # arcpy.Delete_management('point_select_1')
                # arcpy.Delete_management('split_lines_3')

                # 2.5.5.обработка выбранной линии
                # 2.5.5.1. добавление атрибута геометрии (длины)
                arcpy.management.AddGeometryAttributes('select_line', "LENGTH","METERS")
                values_len_line = [i[0] for i in arcpy.da.SearchCursor('select_line', "LENGTH")]
                value_len_line = values_len_line[0]
                # 2.5.5.2. уплотнение вершин линии до размера ячейки исходной цмр
                arcpy.edit.Densify('select_line', "DISTANCE", cell_p)
                arcpy.management.FeatureVerticesToPoints('select_line', "point_select_line", "ALL")
                # 2.5.5.3. извлечение значений углов наклона в каждой точке
                arcpy.sa.ExtractValuesToPoints('point_select_line', slope_degree, "select_point_value_slope")
                values_slope = [i[0] for i in arcpy.da.SearchCursor('select_point_value_slope', "RASTERVALU")]
                # 2.5.5.4. создание списка вершин, в которых значение угла наклона больше 20 градусов

                point_list_20 = []
                points_max_20 = [values_slope.index(i) for i in values_slope if i > 21]
                # 2.5.5.4. выбор и добавление в список точек перегиба (перехода между 20 градусами)
                for i in range(len(points_max_20)):
                    query_len_slope = '"OBJECTID" = {0}'.format(points_max_20[i])
                    point_extr_20 = 'point_%s_extr_20' % (i+1)
                    arcpy.MakeFeatureLayer_management('select_point_value_slope', point_extr_20, query_len_slope)
                    point_list_20.append(point_extr_20)
                # 2.5.5.5. объединение точек перегиба
                arcpy.Merge_management(point_list_20, "point_thr_ext_20")
                # 2.5.5.6. разрезание выбранной линии по точкам перегиба (в результате много коротких линий с углом больше 20 и есть длинные линии с углом меньше 20)
                arcpy.management.SplitLineAtPoint('select_line', 'point_thr_ext_20', "line_thr_ext_20", "1 Meters")
                arcpy.management.AddGeometryAttributes('line_thr_ext_20', "LENGTH","METERS")
                # 2.5.5.7. сортировка по длине (сначала будут линии с углом меньше 20 градусов)
                arcpy.management.Sort('line_thr_ext_20', "line_thr_ext_sort_20", [["LENGTH", "DESCENDING"]])
                values_slope_max_20 = [i[0] for i in arcpy.da.SearchCursor('line_thr_ext_sort_20', "LENGTH")]
                value_slope_max_20 = values_slope_max_20[0]
                percent_line_20 = value_slope_max_20*100/value_len_line
                # 2.5.5.7. есть два преобладающих отрезка
                if percent_line_20 >= 20:
                    arcpy.AddMessage('use percent_line_20 >= 20')
                    query_line_20_25 = '"OBJECTID" = 1'
                    arcpy.MakeFeatureLayer_management('line_thr_ext_sort_20', "line_thr_min_20", query_line_20_25)
                    arcpy.FeatureVerticesToPoints_management('line_thr_min_20', "point_thr_start_end_20", "BOTH_ENDS")
                    arcpy.sa.ExtractValuesToPoints('point_thr_start_end_20', DEM_fill, "point_thr_start_end_height_20")
                    arcpy.management.Sort('point_thr_start_end_height_20', "point_thr_start_end_height_sort_20", [["RASTERVALU", "DESCENDING"]])
                    query_point_20 = '"OBJECTID" = 1'
                    arcpy.MakeFeatureLayer_management('point_thr_start_end_height_sort_20', "point_zone_20", query_point_20)
                    arcpy.AddMessage('Slope 20 ok')

                if percent_line_20 < 20:
                    arcpy.AddMessage('use percent_line_20 < 20')
                    arcpy.management.AddGeometryAttributes('point_select_line', "POINT_X_Y_Z_M","METERS")
                    arcpy.sa.ExtractValuesToPoints('point_select_line', DEM_fill, "select_point_value")
                    flds = ['POINT_X', 'POINT_Y', 'RASTERVALU']
                    # 2.5.5.8.2. создание списков для каждой координаты
                    px = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "POINT_X")][0]
                    py = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "POINT_Y")][0]
                    pz = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "RASTERVALU")][0]
                    angle = []
                    cnt = 0
                    with arcpy.da.SearchCursor('select_point_value', flds) as cursor:
                        for i in cursor:
                            # 2.5.5.8.3. проход по каждой точке (за исключением первой и второй от вершины)
                            if cnt >= 2:
                                # 2.5.5.8.4. извлечение двух точек - первой и итерируемой
                                selection_query = '"OBJECTID" = {0} OR "OBJECTID" = {1}'.format(0, cnt)
                                # 2.5.5.8.5. добавление точек на новый слой
                                arcpy.MakeFeatureLayer_management('select_point_value', "current_points", selection_query)
                                # 2.5.5.8.6. разрезание линии по двум точкам
                                arcpy.management.SplitLineAtPoint('select_line', 'current_points', "splitted_fclass", "1 Meters")
                                line_length = 0
                                # 2.5.5.8.7. поиск тангенса угла между двумя точками
                                for row in arcpy.da.SearchCursor('splitted_fclass', ["SHAPE@", "SHAPE@LENGTH"]):
                                    if (row[0].firstPoint.X == px and row[0].firstPoint.Y == py):
                                        line_length = row[1]                                    
                                        break
                                if (line_length != 0):
                                    tg_A = (pz - i[2]) / line_length
                                    angle.append(math.degrees(math.atan(tg_A)))
                                    arcpy.Delete_management('current_points')
                                    arcpy.Delete_management('splitted_fclass')
                                else:
                                    arcpy.AddMessage('Zero Division Error')
                                    arcpy.Delete_management('current_points')
                                    arcpy.Delete_management('splitted_fclass')
                            cnt += 1
                    point_max = [angle.index(i) for i in angle if i <= 21][1]
                    query_len_slope_2 = '"OBJECTID" = {0}'.format(point_max)
                    arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_20", query_len_slope_2)
                    arcpy.AddMessage('Slope 20 ok')

                arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_zone_20', "tranzit_end", "1 Meters")  

                # 2.5.5.8.9. поиск верхней из двух линий
                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        break
                objval_1 = 0
                with arcpy.da.SearchCursor('tranzit_end', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        if (coords_start == split_start):
                            objval_1 = row[1]
                            break
                query_line_1 = '"OBJECTID" = {0}'.format(objval_1)
                aval_tranz_zone = arcpy.MakeFeatureLayer_management('tranzit_end', aval_tranz_zone, query_line_1)

                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('tranzit_end', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        if (coords_end == split_end):
                            objval_2 = row[1]
                            break
                query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
                arcpy.MakeFeatureLayer_management('tranzit_end', "runout_line_no_angle", query_line_2)
                break

        arcpy.AddMessage('Line tranzit zone end ok')

        # уплотняем зону осаждения по размеру ячейки
        arcpy.edit.Densify('runout_line_no_angle', "DISTANCE", cell_p)
        # превращаем линию в точки
        arcpy.management.FeatureVerticesToPoints('runout_line_no_angle', "point_runout_line_no_angle", "ALL")
        # добавляем координаты x и y
        arcpy.management.AddGeometryAttributes('point_runout_line_no_angle', "POINT_X_Y_Z_M","METERS")
        flds = ['POINT_X', 'POINT_Y']
        # 2.5.5.8.2. создание списков для каждой координаты
        px = [i[0] for i in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_X")]
        py = [i[0] for i in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_Y")]
        angle_r = []
        tan_threshol = 30
        # начинаем проходить по каждой точке и искать дирекционный угол на следующую точку
        for i in range(len(px) - 1):
            ro_x = abs(px[i] - px[i+1])
            ro_y = abs(py[i] - py[i+1])
            razn_x = px[i] - px[i+1]
            razn_y = py[i] - py[i+1]
            if razn_x == 0:
                angle_i = 0
            if razn_y == 0:
                angle_i = 90
            if razn_x > 0 and razn_y > 0:
                tan_a = ro_x/ro_y
                angle_i = math.degrees(math.atan(tan_a)) + 180
            if razn_x > 0 and razn_y < 0:
                tan_a = ro_x/ro_y
                angle_i = 360 - math.degrees(math.atan(tan_a))
            if razn_x < 0 and razn_y > 0:
                tan_a = ro_x/ro_y
                angle_i = 180 - math.degrees(math.atan(tan_a))
            if razn_x < 0 and razn_y < 0:
                tan_a = ro_x/ro_y
                angle_i = math.degrees(math.atan(tan_a))
            angle_r.append(angle_i)
        
        angle_thresh = []

        for i in range(len(angle_r) - 1):
            razn_angl = abs(angle_r[i] - angle_r[i+1])
            angle_thresh.append(razn_angl)
        points_thres = [angle_thresh.index(i) for i in angle_thresh if i >= tan_threshol]
        thresh_angle_point = []
        for i in range(len(points_thres)):
            angles_i = []
            point_it_all = points_thres[i]
            px_i = [k[0] for k in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_X")][i]
            py_i = [k[0] for k in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_Y")][i]
            for t in range(20):
                id_t = i+t+1
                px_i_t = [k[0] for k in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_X")][id_t]
                py_i_t = [k[0] for k in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_Y")][id_t]
                ro_x_i = abs(px_i - px_i_t)
                ro_y_i = abs(py_i - py_i_t)
                razn_y_f = round(py_i - py_i_t)
                if (razn_y_f <= 0):
                    angle_i = ro_y_i / ro_x_i
                else:
                    angle_i = ro_x_i / ro_y_i
                angles_i.append(angle_i)
            point_start = angles_i[0]
            point_end = angles_i[-1]
            if point_start >= point_end:
                thresh_angle_point.append(point_it_all)
        if len(thresh_angle_point) != 0:
            query_point_30 = '"OBJECTID" = {0}'.format(thresh_angle_point[0] - 1)
            arcpy.MakeFeatureLayer_management('point_runout_line_no_angle', "runout_zone_point_30",query_point_30)
            arcpy.management.SplitLineAtPoint('runout_line_no_angle', 'runout_zone_point_30', "tranzit_end_30", "1 Meters")
            arcpy.management.AddGeometryAttributes('tranzit_end_30', "LENGTH","METERS")
            len_runout_after_30_degree = [i[0] for i in arcpy.da.SearchCursor('slope_line_25_sort', "LENGTH")][-1]
            arcpy.MakeFeatureLayer_management('runout_zone_point_30', "30_degree")
            arcpy.MakeFeatureLayer_management('point_zone_20', "20_degree")
            point_list_interest_point = ['20_degree','25_degree', '30_degree']

        else:
            arcpy.MakeFeatureLayer_management('point_zone_20', "20_degree")
            point_list_interest_point = ['20_degree','25_degree']


        arcpy.AddMessage('Point 30 ok')
        
        # # Этап 3. Поиск полигона зоны зарождения
        # 3.1. поиск изогоны со значением 25 градусов
        # 3.1.1. создание искусственной поверхности из растра углов наклона (умноженной на значимое число)
        slope_100 = slope_degree * 100
        # 3.1.2. заполнение провалов в полученном растре (позволяет без агрегирования убрать небольшие локальные спрямления)
        Slope_fill = arcpy.sa.Fill(slope_100)
        # 3.1.3. переклассификация растра, необходима для создания целочисленного растра с углами больше 25 градусов и меньше 25 градусов
        remap = arcpy.sa.RemapRange([[0,2500,0],[2500,6000,1],[6000,9000,0]])
        slope_reclass = arcpy.sa.Reclassify(Slope_fill, "Value", remap, "NODATA")
        # 3.1.4. превращение растра в полигоны и отбор (оставляются только полигоны с углами наклона более25 градусов)
        arcpy.conversion.RasterToPolygon(slope_reclass, "slope_polygon", "NO_SIMPLIFY", "Value")
        query_slope = '"gridcode" = 1'
        # 3.1.5.превращение полигонов в линии
        arcpy.MakeFeatureLayer_management('slope_polygon', "slope_poly_25", query_slope)
        arcpy.management.PolygonToLine('slope_poly_25', "slope_line_25")
        # 3.1.6. добавление к линии атрибута геометрии для сортировки и исключения коротких линий
        arcpy.management.AddGeometryAttributes('slope_line_25', "LENGTH","METERS")
        arcpy.management.Sort('slope_line_25', "slope_line_25_sort", [["LENGTH", "DESCENDING"]])
        len_slope_max = [i[0] for i in arcpy.da.SearchCursor('slope_line_25_sort', "LENGTH")][0]
        len_threshold = len_slope_max * 10 / 100
        query_len = '"LENGTH" > {0}'.format(len_threshold)
        arcpy.MakeFeatureLayer_management('slope_line_25', "slope_line_25_len", query_len)
        arcpy.Dissolve_management('slope_line_25_len', "slope_line_dis", "", "", "MULTI_PART", "UNSPLIT_LINES")

        arcpy.analysis.Intersect(["slope_line_dis", aval_tranz_zone] , "inter_slope_25_to_split", "", "", "POINT")
        arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'inter_slope_25_to_split', "stream_25_line_split", "1 Meters")
        arcpy.management.AddGeometryAttributes('stream_25_line_split', "LENGTH","METERS")
        arcpy.management.Sort('stream_25_line_split', "stream_25_line_split_sort", [["LENGTH", "DESCENDING"]])
        query_most_len_line = '"OBJECTID" = 1'
        arcpy.MakeFeatureLayer_management('stream_25_line_split_sort',  "most_len_line", query_most_len_line)

        # 3.2.1. создание растра водораздела и конвертация его в вектор
        out_watershed_raster = arcpy.sa.Watershed(flow_directions, 'point_zone_20')
        arcpy.conversion.RasterToPolygon(out_watershed_raster, "out_watershed_polygon", "NO_SIMPLIFY", "Value")
        # 3.2.2. конвертация из полигона в линию
        arcpy.MakeFeatureLayer_management('out_watershed_polygon', "watershed_poly")
        arcpy.management.PolygonToLine('watershed_poly', "watershed_line")
        # 3.2.3. разрезание изогоны 25 градусов и линий водоразделов по точкам пересечения
        arcpy.FeatureVerticesToPoints_management('watershed_line', "watershed_vertex", "ALL")
        arcpy.management.SplitLineAtPoint('watershed_line', 'watershed_vertex', "watershed_line_split_vertex", "1 Meters")
        arcpy.FeatureVerticesToPoints_management('slope_line_dis', "slope_layer_inter_vertex", "ALL")
        arcpy.management.SplitLineAtPoint('slope_line_dis', 'slope_layer_inter_vertex', "slope_layer_split_vertex", "1 Meters")
        arcpy.analysis.Intersect(['slope_layer_split_vertex', 'watershed_line_split_vertex'], "point_output_split_poly", "", "", "POINT")
        arcpy.management.SplitLineAtPoint('slope_layer_split_vertex', 'point_output_split_poly', "slope_layer_inter_split", "1 Meters")
        arcpy.management.SplitLineAtPoint('watershed_line_split_vertex', 'point_output_split_poly', "watershed_line_split", "1 Meters")
        # 3.2.4. сохранение двух линий на один слой
        merge_list_watershed = ["slope_layer_inter_split", "watershed_line_split"]
        arcpy.Merge_management(merge_list_watershed, "watershed_line_25")
        # 3.2.5. создание полигонов из линий
        arcpy.management.FeatureToPolygon('watershed_line_25', "water_polygon_all")
        # 3.2.5. поиск и сохранение полигона, пересекающего тальвег

        arcpy.MakeFeatureLayer_management('water_polygon_all',  "water_polygon_all_fl")
        arcpy.management.SelectLayerByLocation('water_polygon_all_fl', "INTERSECT", 'most_len_line')
        arcpy.MakeFeatureLayer_management('water_polygon_all_fl', "watershed_intersect")
        arcpy.management.AddGeometryAttributes('watershed_intersect', "AREA", "", "SQUARE_METERS")
        arcpy.management.Sort('watershed_intersect', "watershed_intersect_sort", [["POLY_AREA", "DESCENDING"]])
        query_area_poly = '"OBJECTID" = 1'
        watershed_output = arcpy.MakeFeatureLayer_management('watershed_intersect_sort', watershed_output, query_area_poly)

        arcpy.AddMessage('Start zone polygon ok')

        # Разворачиваем линию так, чтобы счет шел снизу вверх, а не сверху вниз
        aval_tranz_zone_flip = arcpy.edit.FlipLine(aval_tranz_zone)
        # Ищем пересечения развернутой линии и полигона водораздела
        arcpy.analysis.Intersect([watershed_output, aval_tranz_zone_flip] , "intersect_point_slope_25", "", "", "POINT")
        # результатом поиска будут мультиточки, поэтому ищем просто точки
        arcpy.management.MultipartToSinglepart('intersect_point_slope_25', "intersect_point_25_sing")
        # к развернутой линии добавляем параметр длины для того, чтобы узнать суммарную длину зоны транзита и зоны зарождения
        arcpy.management.AddGeometryAttributes(aval_tranz_zone_flip, "LENGTH","METERS")
        len_all_line = [i[0] for i in arcpy.da.SearchCursor(aval_tranz_zone_flip, "LENGTH")][0]
        # задаем параметр процента длины от общей длины
        len_treshold_line = len_all_line * 20 / 100
        point_list = []
        # делаем список из id точек
        inter_point = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")]
        # начинаем проходить по списку 
        for i in range(len(inter_point)):
            point_i = 'point_i_%s' % (i+1)
            # от первой до предпоследней точки извлекаем эту точку и следующую, так как i начинается с 0, берем i+1 и i+2
            if i < len(inter_point) - 1:
                query_inter_poin = '"OBJECTID" = {0} OR "OBJECTID" = {1}'.format((i+1),(i+2))
                arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
                # режем линию по этим двум точкам (1 линия - сверху, посередине, последняя линия - снизу, нам нужна та, что в серединке)
                arcpy.management.SplitLineAtPoint(aval_tranz_zone_flip, 'i_point', "i_stream", "1 Meters")
                with arcpy.da.SearchCursor(aval_tranz_zone_flip, 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        if (coords_start != split_start and coords_end != split_end):
                            objval_2 = row[1]
                            break
                query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
            # если точка последняя, то режем по ней и берем первую линию
            else:
                query_inter_poin = '"OBJECTID" = {0}'.format(i+1)
                arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
                arcpy.management.SplitLineAtPoint(aval_tranz_zone_flip, 'i_point', "i_stream", "1 Meters")
                with arcpy.da.SearchCursor(aval_tranz_zone_flip, 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_start = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_start = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        if (coords_start == split_start):
                            objval_2 = row[1]
                            break
                query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
            arcpy.MakeFeatureLayer_management('i_stream', "i_stream_interest", query_line_2)
            # результатом является линия между двумя точками или последняя линия
            # к ней добавляем длину в метрах и извлекаем ее
            arcpy.management.AddGeometryAttributes('i_stream_interest', "LENGTH","METERS")
            len_i_line = [k[0] for k in arcpy.da.SearchCursor('i_stream_interest', "LENGTH")][0]
            # если длина выбранной линии больше порога, то заходим в цикл
            if len_i_line >= len_treshold_line:
                query_inter_poin_interest = '"OBJECTID" = {0}'.format(i+1)
                # добавляем начальную точку в общий список под уникальным именем
                arcpy.MakeFeatureLayer_management('intersect_point_25_sing', point_i, query_inter_poin_interest)
                point_list.append(point_i)
            arcpy.Delete_management('i_point')
            arcpy.Delete_management('i_stream')
            arcpy.Delete_management('i_stream_interest')

        # создаем единый массив точек
        arcpy.Merge_management(point_list, "point_intersect_len")
        # смотрим на длину массива
        count_line_i = [k[0] for k in arcpy.da.SearchCursor('point_intersect_len', "OBJECTID")]
        query_point_25 = '"OBJECTID" = {0}'.format(count_line_i[0])
        # находим точку перегиба 
        arcpy.MakeFeatureLayer_management('point_intersect_len', "point_25_degree_end", query_point_25)

        # дальше смотрим на то, нет ли пересечений сверху и если есть, то выделяем его
        # находим верхнюю точку НЕ перевернутой линии
        arcpy.FeatureVerticesToPoints_management(aval_tranz_zone, "start_end_point", "BOTH_ENDS")
        arcpy.sa.ExtractValuesToPoints('start_end_point', DEM_fill, "start_end_point_xyz")
        s_e_points = [i[0] for i in arcpy.da.SearchCursor('start_end_point_xyz', "RASTERVALU")]
        razn_z_start_end = s_e_points[0]-s_e_points[1]
        if razn_z_start_end > 0:
            query_point_start_end = '"OBJECTID" = 1'
        else:
            query_point_start_end = '"OBJECTID" = 2'
        arcpy.MakeFeatureLayer_management('start_end_point_xyz', "start_point", query_point_start_end)
        # смотрим есть ли пересечение этой точки и водотока (выделение инвертируем)
        arcpy.management.SelectLayerByLocation('start_point' , "INTERSECT", watershed_output , "","NEW_SELECTION", "INVERT")
        # если пересечений нет, то значит точка лежит выше полигона водораздела и мы должны найти точку пересечения
        arcpy.MakeFeatureLayer_management('start_point', "start_point_inter")
        len_inter_0 = len([i[0] for i in arcpy.da.SearchCursor('start_point_inter', "OBJECTID")])
        if len_inter_0 != 0:
            # в случае, если точка лежит выше водораздела, то точкой пересечения с линией в 25 градусов считаем верхнюю из точек пересечения
            start_point_25 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")][-1]
            query_start_point_25 = '"OBJECTID" = {0}'.format(start_point_25)
            arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "point_25_degree_start", query_start_point_25) #point_25_degree_start
            point_start_end = ["point_25_degree_end", 'point_25_degree_start']
            arcpy.Merge_management(point_start_end, "point_25_degree")
            arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'point_25_degree', "line_25_degree", "1 Meters")
        else:
            arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'point_25_degree_end', "line_25_degree", "1 Meters")

        arcpy.AddMessage('Point 25 ok')

        arcpy.MakeFeatureLayer_management('point_25_degree_end', "25_degree")
        arcpy.Merge_management(point_list_interest_point, "point_20_25_30")

        arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_20_25_30', "avalanche_path_component", "1 Meters") 
        query_start = '"OBJECTID" = 1'
        query_tranzit = '"OBJECTID" = 2'
        query_runout = '"OBJECTID" = 3'
        arcpy.MakeFeatureLayer_management('avalanche_path_component', "start_zone_line", query_start)
        arcpy.MakeFeatureLayer_management('avalanche_path_component', "tranzit_zone_line", query_tranzit)
        arcpy.MakeFeatureLayer_management('avalanche_path_component', "runout_zone_line", query_runout)

        len_path_comp_count = len([i[0] for i in arcpy.da.SearchCursor('avalanche_path_component', "OBJECTID")])

        arcpy.AddMessage('Line zone ok')


        if len_path_comp_count == 4:
            arcpy.FeatureVerticesToPoints_management('tranzit_zone_line', "start_end_point_tranzit", "BOTH_ENDS")
            arcpy.management.AddGeometryAttributes('start_end_point_tranzit', "POINT_X_Y_Z_M","METERS")
            arcpy.management.AddGeometryAttributes('runout_zone_point_30', "POINT_X_Y_Z_M","METERS")

            px_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_X")]
            py_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_Y")]

            px_r = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_X")][0]
            py_r = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_Y")][0]

            razn_tranzit_x = px_t[0] - px_t[1]
            razn_tranzit_y = py_t[0] - py_t[1]

            ro_x_t = abs(razn_tranzit_x)
            ro_y_t = abs(razn_tranzit_y)

            if razn_tranzit_x == 0:
                angle_t = 0
            if razn_tranzit_y == 0:
                angle_t = 90
            if razn_tranzit_x > 0 and razn_tranzit_y > 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = math.degrees(math.atan(tan_a)) + 180
            if razn_tranzit_x > 0 and razn_tranzit_y < 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = 360 - math.degrees(math.atan(tan_a))
            if razn_tranzit_x < 0 and razn_tranzit_y > 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = 180 - math.degrees(math.atan(tan_a))
            if razn_tranzit_x < 0 and razn_tranzit_y < 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = math.degrees(math.atan(tan_a))

            arcpy.AddMessage('angle_t %s' % angle_t)
            arcpy.AddMessage('len %s' % len_runout_after_30_degree)

            arcpy.AddMessage('angle_t %s' % angle_t)
            arcpy.AddMessage('len %s' % len_runout_after_30_degree)

            if angle_t > 0 and angle_t <= 90:
                angle_len = 90 - angle_t
            if angle_t > 90 and angle_t <= 180:
                angle_len = angle_t - 90
            if angle_t > 180 and angle_t <= 270:
                angle_len = 270 - angle_t
            if angle_t > 270 and angle_t <= 360:
                angle_len = angle_t - 270
            
            arcpy.AddMessage('angle_len %s' % angle_len)
            cos_angle_len = math.cos(angle_len)
            sin_angle_len = math.sin(angle_len)

            arcpy.AddMessage('cos_angle_len %s' % cos_angle_len)
            arcpy.AddMessage('sin_angle_len %s' % sin_angle_len)

            d_x = len_runout_after_30_degree * cos_angle_len
            d_y = len_runout_after_30_degree * sin_angle_len

            arcpy.AddMessage('d_x %s' % d_x)
            arcpy.AddMessage('d_y %s' % d_y)

            x_new = px_r + d_x
            y_new = py_r + d_y

            arcpy.AddMessage('x_new %s' % x_new)
            arcpy.AddMessage('y_new %s' % y_new)

            arcpy.AddMessage('coord_syst %s' % coord_syst)

            sr = arcpy.SpatialReference()
            coord_syst_wkt = '%s' % coord_syst
            sr.loadFromString(coord_syst_wkt)

            pt = arcpy.Point(x_new, y_new)
            pt_geometry = arcpy.PointGeometry(pt, sr)
            
            point_output = arcpy.MakeFeatureLayer_management(pt_geometry, point_output)



        











        










        




        




        
        


            


        
        





        # Добавить удаление всех промежуточных слоев, сохранение промежуточных водораздела и пути не во временные?. Добавить месседжы, исправить названия в окне ввода.
        # обрезать зз сверху по 25
        # благовещенский определение лавинных нагрузок 62-63