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
        

        parameters = [DEM_input, input_mask, select_watercourses, aval_tranz_zone, out_stream_links, point_output, watershed_output

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

        aval_tranz_zone = parameters[3].valueAsText


        out_stream_links = parameters[4].valueAsText
        point_output = parameters[5].valueAsText
        watershed_output = parameters[6].valueAsText


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
        arcpy.AddMessage('count_vertex: %s' % count_vertex)
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
        slope_treshold = [19, 24]
        k = 1
        # 2.5. поиск точки перегиба 
        for s in slope_treshold:
            arcpy.AddMessage('slope: %s degree' % s)
            k = 1
            
            while True:
                # 2.5.1. создание двух списков из единого (в один записываются индексы всех точек, у которых значение угла наклона больше 20 градсов, в другой - меньше 20)
                points_upper = [values_input.index(i) for i in values_input if i > s]
                points_below = [values_input.index(i) for i in values_input if i <= s]
                # 2.5.2. если индексы начала и конца двух списков совпадают, то существует только одна точка перегиба - искомая точка 
                if (points_below[0] == points_upper[-1]):
                    boolval = False
                    query_point_end_1 = '"OBJECTID" = {0}'.format(points_below[0])
                    if s == 20:
                        arcpy.MakeFeatureLayer_management('out_point', "point_zone_20", query_point_end_1)
                        arcpy.AddMessage('Slope 20 ok')
                    else:
                        arcpy.MakeFeatureLayer_management('out_point', "point_zone_25", query_point_end_1)
                        arcpy.AddMessage('Slope 25 ok')
                    
                # 2.5.3. агрегирование исходной ЦМР
                else:
                    # 2.5.3.1. подготовка к агрегированию
                    k = int(k+1)
                    arcpy.AddMessage('iteration: %s' % k)
                    cell_agg = cell_p*k
                    # 2.5.3.2. удаление переменных, полученных на прошлом этапе итерации (ИСПРАВИТЬ И ДОБАВИТЬ)
                    del values_input[:]
                    arcpy.Delete_management('DEM_agg')
                    arcpy.Delete_management('dens_copy_k')
                    arcpy.Delete_management('slope_degree_agg')
                    arcpy.Delete_management('intersect_point_agg')
                    arcpy.Delete_management('out_point_agg')
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
                        # 2.5.5.обработка выбранной линии
                        arcpy.AddMessage('Select line ok')
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
                        points_max = [values_slope.index(i) for i in values_slope if i > s]
                        point_list = []
                        # 2.5.5.4. выбор и добавление в список точек перегиба (перехода между 20 градусами)
                        for i in range(len(points_max)):
                            query_len_slope = '"OBJECTID" = {0}'.format(points_max[i])
                            point_extr = 'point_%s_extr' % (i+1)
                            arcpy.MakeFeatureLayer_management('select_point_value_slope', point_extr, query_len_slope)
                            point_list.append(point_extr)
                        # 2.5.5.5. объединение точек перегиба
                        arcpy.Merge_management(point_list, "point_20_ext")
                        # 2.5.5.6. разрезание выбранной линии по точкам перегиба (в результате много коротких линий с углом больше 20 и есть длинные линии с углом меньше 20)
                        arcpy.management.SplitLineAtPoint('select_line', 'point_20_ext', "line_20_ext", "1 Meters")
                        arcpy.management.AddGeometryAttributes('line_20_ext', "LENGTH","METERS")
                        # 2.5.5.7. сортировка по длине (сначала будут линии с углом меньше 20 градусов)
                        arcpy.management.Sort('line_20_ext', "line_20_ext_sort", [["LENGTH", "DESCENDING"]])
                        values_slope_max = [i[0] for i in arcpy.da.SearchCursor('line_20_ext_sort', "LENGTH")]
                        value_slope_max = values_slope_max[0]
                        percent_line_20 = value_slope_max*100/value_len_line
                        # 2.5.5.7. если длина первой линии (которая меньше 20 градусов) составляет 10 процентов или более от исходной (выбранной) линии, то ее начало считается точкой перегиба
                        if percent_line_20 >= 10:
                            query_line_20 = '"OBJECTID" = 1'
                            arcpy.MakeFeatureLayer_management('line_20_ext_sort', "line_20_min", query_line_20)
                            arcpy.FeatureVerticesToPoints_management('line_20_min', "point_20_start_end", "BOTH_ENDS")
                            arcpy.sa.ExtractValuesToPoints('point_20_start_end', DEM_fill, "point_20_start_end_height")
                            arcpy.management.Sort('point_20_start_end_height', "point_20_start_end_height_sort", [["RASTERVALU", "DESCENDING"]])
                            query_point_20 = '"OBJECTID" = 1'
                            if s == 20:
                                arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_20", query_point_20)
                                arcpy.AddMessage('Slope 20 ok')
                            else:
                                arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_25", query_point_20)
                                arcpy.AddMessage('Slope 25 ok')
                        # 2.5.5.8. если нет четкого разделения по длине, то реализуется следующий цикл
                        else:
                            # 2.5.5.8.1. добавление координат к каждой вершине выбранной линии
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
                                        arcpy.MakeFeatureLayer_management('select_point_value', 'current_points', selection_query)
                                        # 2.5.5.8.6. разрезание линии по двум точкам
                                        arcpy.management.SplitLineAtPoint('select_line', 'current_points', 'splitted_fclass', "1 Meters")
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
                            # 2.5.5.8.8. поиск первой точки, где тангенс угла стал меньше 20 градусов
                            arcpy.AddMessage(angle)
                            point_max = [angle.index(i) for i in angle if i <= s][0]
                            query_len_slope_2 = '"OBJECTID" = {0}'.format(point_max)
                            if s == 20:
                                arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_20", query_len_slope_2)
                                arcpy.AddMessage('Slope 20 ok')
                            else:
                                arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_25", query_len_slope_2)
                                arcpy.AddMessage('Slope 25 ok')
                            
                        
                        # 2.5.5.8.9. разрезание линии по выбранной точке
                        # arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_output_end', "line_with_end_point", "1 Meters")
                        # # 2.5.5.8.9. поиск верхней из двух линий
                        # with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                        #     for row in cursor:
                        #         coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        #         break
                        # objval_1 = 0
                        # with arcpy.da.SearchCursor('line_with_end_point', ['SHAPE@', 'OID@']) as cursor:
                        #     for row in cursor:
                        #         split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        #         if (coords_start == split_start):
                        #             objval_1 = row[1]
                        #             break
                        # query_line_1 = '"OBJECTID" = {0}'.format(objval_1)
                        # aval_tranz_zone = arcpy.MakeFeatureLayer_management('line_with_end_point', aval_tranz_zone, query_line_1)
                        break
        arcpy.AddMessage('Point end ok')
        point_20_25 = ["point_zone_20", "point_zone_25"]
        arcpy.Merge_management(point_20_25, "point_intersect_20_25_degree")
        aval_tranz_zone = arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_intersect_20_25_degree', aval_tranz_zone, "1 Meters")


        # Этап 3. Поиск зоны зарождения
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
        out_watershed_raster = arcpy.sa.Watershed(flow_directions, 'point_output_end')
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

        arcpy.AddMessage('Watershed ok')

        # aval_tranz_zone_flip = arcpy.edit.FlipLine(aval_tranz_zone)
        # arcpy.analysis.Intersect([watershed_output, aval_tranz_zone_flip] , "intersect_point_slope_25", "", "", "POINT")
        # arcpy.management.MultipartToSinglepart('intersect_point_slope_25', "intersect_point_25_sing")
        # arcpy.management.AddGeometryAttributes(aval_tranz_zone, "LENGTH","METERS")
        # len_all_line = [i[0] for i in arcpy.da.SearchCursor(aval_tranz_zone, "LENGTH")][0]
        # len_treshold_line = len_all_line * 20 / 100
        # point_list = []
        # inter_point = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")]
        # for i in range(len(inter_point)):
        #     point_i = 'point_i_%s' % (i+1)
        #     if i < len(inter_point) - 1:
        #         query_inter_poin = '"OBJECTID" = {0} OR "OBJECTID" = {1}'.format((i+1),(i+2))
        #         arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
        #         arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'i_point', "i_stream", "1 Meters")
        #         with arcpy.da.SearchCursor(aval_tranz_zone, 'SHAPE@') as cursor:
        #             for row in cursor:
        #                 coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
        #                 coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
        #                 break
        #         objval_2 = 0
        #         with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
        #             for row in cursor:
        #                 split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
        #                 split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
        #                 if (coords_start != split_start and coords_end != split_end):
        #                     objval_2 = row[1]
        #                     break
        #         query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
        #     else:
        #         query_inter_poin = '"OBJECTID" = {0}'.format(i+1)
        #         arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
        #         arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'i_point', "i_stream", "1 Meters")
        #         with arcpy.da.SearchCursor(aval_tranz_zone, 'SHAPE@') as cursor:
        #             for row in cursor:
        #                 coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
        #                 break
        #         objval_2 = 0
        #         with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
        #             for row in cursor:
        #                 split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
        #                 if (coords_start == split_start):
        #                     objval_2 = row[1]
        #                     break
        #         query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
        #     arcpy.MakeFeatureLayer_management('i_stream', "i_stream_interest", query_line_2)

        #     arcpy.management.AddGeometryAttributes('i_stream_interest', "LENGTH","METERS")
        #     len_i_line = [k[0] for k in arcpy.da.SearchCursor('i_stream_interest', "LENGTH")][0]
        #     if len_i_line >= len_treshold_line:
        #         query_inter_poin_interest = '"OBJECTID" = {0}'.format(i+1)
        #         arcpy.MakeFeatureLayer_management('intersect_point_25_sing', point_i, query_inter_poin_interest)
        #         point_list.append(point_i)
        #     arcpy.Delete_management('i_point')
        #     arcpy.Delete_management('i_stream')
        #     arcpy.Delete_management('i_stream_interest')

        # arcpy.AddMessage('point_list %s' % point_list)

        # arcpy.Merge_management(point_list, "point_intersect_len")

        # len_inter_point_1 = [i[0] for i in arcpy.da.SearchCursor('point_intersect_len', "OBJECTID")]
        # len_inter_point = len(len_inter_point_1)
        # arcpy.AddMessage('len_inter_point_1 %s' % len_inter_point_1)
        # arcpy.AddMessage('len_inter_point %s' % len_inter_point)

        # if len_inter_point > 1:
        #     point_id = [i[0] for i in arcpy.da.SearchCursor('point_intersect_len', "OBJECTID")][0]
        #     query_point_25 = '"OBJECTID" = {0}'.format(point_id)
        #     arcpy.MakeFeatureLayer_management('point_intersect_len', "point_25_degree_end", query_point_25)
        # else:
        #     arcpy.MakeFeatureLayer_management('point_intersect_len', "point_25_degree_end")

        # arcpy.FeatureVerticesToPoints_management(aval_tranz_zone, "start_end_point", "BOTH_ENDS")
        # arcpy.sa.ExtractValuesToPoints('start_end_point', DEM_fill, "start_end_point_xyz")
        # s_e_points = [i[0] for i in arcpy.da.SearchCursor('start_end_point_xyz', "RASTERVALU")]
        # razn_z_start_end = s_e_points[0]-s_e_points[1]
        # if razn_z_start_end > 0:
        #     query_point_start_end = '"OBJECTID" = 1'
        # else:
        #     query_point_start_end = '"OBJECTID" = 2'
        # arcpy.MakeFeatureLayer_management('start_end_point_xyz', "start_point", query_point_start_end)
        # arcpy.management.SelectLayerByLocation('start_point' , "INTERSECT", watershed_output , "","NEW_SELECTION", "INVERT")
        # arcpy.MakeFeatureLayer_management('start_point', "start_point_inter")
        # len_inter_0 = len([i[0] for i in arcpy.da.SearchCursor('start_point_inter', "OBJECTID")])
        # if len_inter_0 != 0:
        #     start_point_25 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")][-1]
        #     query_start_point_25 = '"OBJECTID" = {0}'.format(start_point_25)
        #     arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "point_25_degree_start", query_start_point_25) #point_25_degree_start
        #     point_start_end = ["point_25_degree_end", 'point_25_degree_start']
        #     arcpy.Merge_management(point_start_end, "point_25_degree")
        #     out_stream_links = arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'point_25_degree', out_stream_links, "1 Meters")
        # else:
        #     out_stream_links = arcpy.management.SplitLineAtPoint(aval_tranz_zone, 'point_25_degree_end', out_stream_links, "1 Meters")

        










        




        




        
        


            


        
        





        # Добавить удаление всех промежуточных слоев, сохранение промежуточных водораздела и пути не во временные?. Добавить месседжы, исправить названия в окне ввода.
        # обрезать зз сверху по 25
        # благовещенский определение лавинных нагрузок 62-63